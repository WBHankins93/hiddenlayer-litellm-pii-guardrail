# Demo Script

This document outlines the demo sections for the HiddenLayer PII Guardrail project.
Each section is self-contained and can be presented independently.


## 1. Project Overview

Stack: LiteLLM proxy, Microsoft Presidio, Amazon Bedrock, AWS ECS Fargate

The project deploys LiteLLM as a proxy to Amazon Bedrock with a custom guardrail
that intercepts both prompt input and model output. Requests containing PII are
blocked with HTTP 400 before they reach the upstream model.

Currently blocked entity types: email addresses, US Social Security Numbers.

Key files:

    src/guardrails/detectors.py          Detection layer
    src/guardrails/pii_guardrail.py      Orchestration layer
    config/custom_guardrail.py           LiteLLM hook integration
    config/litellm.config.yaml           Proxy and guardrail configuration
    tests/test_pii_detection.py          Pytest suite
    deploy/task-definition.json          ECS Fargate task definition


## 2. Architecture

Reference: docs/architecture.md

Request lifecycle:

    Client
      -> LiteLLM Proxy
      -> pre_call guardrail
      -> PII detection
      -> block (400) or forward
      -> Bedrock
      -> model response
      -> post_call guardrail
      -> PII detection
      -> block or return to client

Two guardrail phases:

    async_pre_call_hook       Scans prompt input before Bedrock receives the request
    async_post_call_success_hook   Scans model output before the client receives the response

IAM design uses two roles:

    Execution role    ECR pull, CloudWatch logs
    Task role         Bedrock invocation at runtime


## 3. Code Walkthrough

### Detection Layer -- src/guardrails/detectors.py

    PIIDetector              Abstract base class with @abstractmethod detect()
    PresidioPIIDetector      NLP-based detection via Presidio AnalyzerEngine
    RegexPIIDetector         Pattern matching for SSN format with word boundary enforcement
    CompositePIIDetector     Aggregates both detectors, deduplicates by (entity_type, start, end)

Design decision: deduplication happens at the composite level, not inside individual
detectors. Both detectors return raw findings. The composite owns the aggregation boundary.

### Orchestration Layer -- src/guardrails/pii_guardrail.py

    BLOCKED_ENTITIES set controls which entity types trigger a block.
    inspect() runs detection and filters findings against blocked entities.
    Adding a new blocked type requires one line change in this set.

### LiteLLM Integration -- config/custom_guardrail.py

    Extends CustomGuardrail from LiteLLM.
    _extract_text_from_messages() handles both string and list content formats.
    _block_if_pii_detected() uses asyncio.to_thread for non-blocking Presidio calls.
    async_post_call_success_hook handles both dict (streaming) and object (standard) response formats.


## 4. Test Suite

Run:

```bash
PYTHONPATH=. pytest tests/ -v
```

Test classes:

    TestPresidioPIIDetector       Presidio detects email, SSN (US_SSN entity type), clean text
    TestRegexPIIDetector          Regex detects SSN format, rejects partial matches, enforces word boundaries
    TestCompositePIIDetector      Combined detection, deduplication verification
    TestPIIGuardrail              Allow/block decisions, mixed PII, non-blocked entity passthrough

Notable: Presidio internally denylists known fake SSNs (e.g., 123-45-6789).
Tests use 433-77-9090 to avoid Presidio's invalidate_result filter.


## 5. Live Demo

### Prerequisites

```bash
export BASE_URL=http://<ecs-public-ip>:4000
export LITELLM_MASTER_KEY=<key>
```

### Test 1: Email PII Blocking

```bash
curl -s "$BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "bedrock-jamba", "messages": [{"role": "user", "content": "My email is test@example.com"}]}'
```

Expected: HTTP 400

```json
"detected_entities": ["EMAIL_ADDRESS"]
```

### Test 2: SSN PII Blocking

```bash
curl -s "$BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "bedrock-jamba", "messages": [{"role": "user", "content": "My SSN is 123-45-6789"}]}'
```

Expected: HTTP 400

```json
"detected_entities": ["US_SOCIAL_SECURITY_NUMBER"]
```

### Test 3: Safe Prompt (Bedrock Pass-Through)

```bash
curl -s "$BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "bedrock-jamba", "messages": [{"role": "user", "content": "What is machine learning?"}], "max_tokens": 50}'
```

Expected: Bedrock model response, or 429 if daily token quota is exhausted.

If 429: the error confirms authentication, IAM role assumption, model routing, and
Bedrock API invocation all function correctly. The quota limitation is an AWS account
provisioning constraint on new accounts, not a code or configuration issue.
See docs/troubleshooting.md for the full investigation.

### Test 4: Groq Fallback (Provider-Agnostic Demo)

```bash
curl -s "$BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "groq-llama", "messages": [{"role": "user", "content": "What is machine learning?"}], "max_tokens": 50}'
```

Expected: Model response from Groq. Demonstrates the guardrail works identically
regardless of which LLM backend is behind the proxy.

### Test 5: Groq PII Blocking

```bash
curl -s "$BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "groq-llama", "messages": [{"role": "user", "content": "My email is test@example.com"}]}'
```

Expected: HTTP 400 -- same PII blocking behavior as Bedrock-routed requests.

### Test 6: Model List

```bash
curl -s "$BASE_URL/v1/models" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY"
```

Expected: JSON listing bedrock-nova, bedrock-jamba, and groq-llama.


## 6. AWS Deployment

Reference: docs/aws-deployment.md

### Issues Encountered

    OOM exit code 137         Initial task used 1024 MB, Presidio + spaCy exceeded it
    Hardcoded secret          Remediated with Secrets Manager, rotated the exposed key
    Docker build context      Dockerfile in deploy/ required building from repo root
    Image vulnerabilities     Selected python:3.11-slim for lower CVE count vs bookworm

All issues documented in docs/troubleshooting.md with root cause and resolution.