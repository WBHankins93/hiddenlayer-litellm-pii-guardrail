# HiddenLayer LiteLLM PII Guardrail

A custom PII detection guardrail for LiteLLM deployed on AWS ECS Fargate. The guardrail intercepts both prompt input and model output, blocking requests that contain sensitive data before they reach the upstream model.

Built with Microsoft Presidio for NLP-based entity recognition, supplemented by regex pattern matching for high-confidence detections like US Social Security Numbers.

## Architecture

```
Client Request
    |
ECS Fargate Service
    |
LiteLLM Proxy
    |
Custom PII Guardrail (pre_call + post_call)
    |
PII Detection (Presidio + Regex)
    |
Block (400) or Forward to Bedrock
```

See [docs/architecture.md](docs/architecture.md) for the full Mermaid diagram, request lifecycle, and IAM design.

## Project Structure

```
config/
  litellm.config.yaml       # LiteLLM proxy configuration with model routing and guardrail hooks
  custom_guardrail.py        # LiteLLM integration hook (pre_call and post_call)

src/guardrails/
  detectors.py               # PII detection layer: Presidio, regex, and composite detector
  pii_guardrail.py           # Orchestration layer with blocked entity filtering

tests/
  test_pii_detection.py      # pytest suite covering all detection and guardrail layers

deploy/
  Dockerfile                 # Container image definition (python:3.11-slim)
  task-definition.json       # ECS Fargate task definition with Secrets Manager integration

docs/
  architecture.md            # System architecture and deployment design
  aws-deployment.md          # Full AWS deployment walkthrough with CLI commands
  demo-script.md             # Presentation demo script with expected outputs
  troubleshooting.md         # Issues encountered and resolutions

examples/
  curl_examples.sh           # Validation script for testing guardrail and model endpoints
```

## How It Works

The guardrail uses a composite detection pattern. Two detectors run against every message:

1. **Presidio Analyzer** -- NLP-based detection for entity types like email addresses, phone numbers, and names
2. **Regex Detector** -- Pattern-based detection for US Social Security Numbers with word boundary enforcement

Results are deduplicated by entity type and character position at the composite aggregation boundary to prevent overlap between detectors flagging the same span.

The `PIIGuardrail` class filters findings against a configurable set of blocked entity types (`BLOCKED_ENTITIES`). Both Presidio's `US_SSN` and the regex detector's `US_SOCIAL_SECURITY_NUMBER` entity types are included to ensure SSNs are caught regardless of which detector identifies them. If any blocked entity is found, LiteLLM returns HTTP 400 before the request reaches Bedrock.

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
PYTHONPATH=. pytest tests/ -v

# Start LiteLLM proxy
PYTHONPATH=. litellm --config config/litellm.config.yaml --port 4000
```

## Testing the Guardrail

```bash
# Should be blocked (contains email)
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -d '{"model": "bedrock-jamba", "messages": [{"role": "user", "content": "My email is test@example.com"}]}'

# Should be blocked (contains SSN)
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -d '{"model": "bedrock-jamba", "messages": [{"role": "user", "content": "My SSN is 123-45-6789"}]}'

# Should pass through to model
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -d '{"model": "groq-llama", "messages": [{"role": "user", "content": "What is machine learning?"}], "max_tokens": 50}'
```

See [docs/demo-script.md](docs/demo-script.md) for the full demo walkthrough with expected outputs.

## Extending Detection

To add a new blocked entity type, add it to `BLOCKED_ENTITIES` in `src/guardrails/pii_guardrail.py`. Presidio supports dozens of entity types out of the box. For custom patterns, add a new detector class that extends `PIIDetector` and register it in `CompositePIIDetector`.

## AWS Deployment

The service runs on ECS Fargate with the master API key stored in AWS Secrets Manager. The proxy is configured with multiple model backends including Amazon Bedrock and Groq.

See [docs/aws-deployment.md](docs/aws-deployment.md) for the full deployment walkthrough and [docs/troubleshooting.md](docs/troubleshooting.md) for issues encountered and resolutions.

### Deploy Steps

```bash
# Build and push container image
docker build -f deploy/Dockerfile -t hiddenlayer-litellm-pii-guardrail .
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker tag hiddenlayer-litellm-pii-guardrail:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/hiddenlayer-litellm-pii-guardrail:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/hiddenlayer-litellm-pii-guardrail:latest

# Register task definition and deploy
aws ecs register-task-definition --cli-input-json file://deploy/task-definition.json --region us-east-1
aws ecs update-service --cluster hiddenlayer-litellm-cluster --service hiddenlayer-litellm-service --force-new-deployment --region us-east-1
```
