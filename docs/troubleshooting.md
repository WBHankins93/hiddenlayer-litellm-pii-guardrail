# Troubleshooting

---

---

## Bedrock daily token quota

If LiteLLM returns a 429 error with:

"Too many tokens per day, please wait before trying again."

the LiteLLM proxy, authentication, and Bedrock model routing are working, but the AWS account has reached the daily token quota for that Bedrock model.

Resolution:
1. Wait for the quota window to reset.
2. Try a different Bedrock model.
3. Request a quota increase in AWS Service Quotas if needed.
4. Continue local guardrail development with mocked model responses while Bedrock quota is unavailable.

---

## Custom guardrail import resolution issues

During LiteLLM startup, the proxy failed to load the custom guardrail with errors similar to:

```txt
ImportError: Could not import HiddenLayerPIIGuardrail from custom_guardrail
```

and

```txt
ModuleNotFoundError: No module named 'config.custom_guardrail'
```

### Root Cause

LiteLLM dynamically imports custom guardrails relative to the config file path. Python package resolution required explicit package initialization and `PYTHONPATH` configuration.

The project structure uses:

```txt
config/custom_guardrail.py
src/guardrails/
```

Without package initialization, Python could not resolve imports correctly during LiteLLM startup.

### Resolution

Added package initialization files:

```bash
touch config/__init__.py
touch src/__init__.py
touch src/guardrails/__init__.py
```

Started LiteLLM with explicit project root pathing:

```bash
PYTHONPATH=. litellm --config config/litellm.config.yaml --port 4000
```

### Key Learning

When LiteLLM dynamically loads custom guardrails, Python module resolution must be configured correctly for local project imports.

Explicit package initialization and `PYTHONPATH` configuration ensured the custom guardrail could successfully import internal detector modules.

---

## Bedrock quota limitation during integration testing

After validating the LiteLLM deployment, custom guardrail integration, and Dockerized runtime, Bedrock began returning the following error for non-blocked prompts:

```txt
litellm.RateLimitError: BedrockException -
"Too many tokens per day, please wait before trying again."
```

### Validation Completed Despite Quota Exhaustion

All components were validated independently: LiteLLM proxy startup, Bedrock authentication, model routing, Docker containerization, custom guardrail loading, PII blocking (email and SSN), and end-to-end request lifecycle.

PII-blocked requests terminate before reaching Bedrock, confirming the guardrail functions correctly regardless of upstream provider quota state.

### Mitigation

Added Groq as a fallback model in litellm.config.yaml. The guardrail operates identically across providers, demonstrating provider-agnostic PII detection.

---

## Hardcoded secret in ECS task definition

### Issue

The `LITELLM_MASTER_KEY` was defined as a plaintext value in the `environment` block of the ECS task definition and committed to version control.

```json
"environment": [
  { "name": "LITELLM_MASTER_KEY", "value": "<plaintext-value>" }
]
```

Environment variables defined this way are visible in the ECS console, the task definition JSON, and git history.

### Why this matters

Hardcoded secrets in version control persist indefinitely in git history even after removal. For API keys and authentication tokens, this creates an exposure window that cannot be closed by simply deleting the value from the current file. The credential must be rotated.

### Remediation

Created a secret in AWS Secrets Manager scoped to this project:

```bash
aws secretsmanager create-secret \
  --name hiddenlayer-litellm/master-key \
  --description "LiteLLM master API key for HiddenLayer PII guardrail project" \
  --secret-string "<value>" \
  --region us-east-1
```

Added a least-privilege inline policy to the ECS execution role restricting access to this single secret:

```bash
aws iam put-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-name SecretsManagerLiteLLMKey \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": "secretsmanager:GetSecretValue",
        "Resource": "<secret-arn>"
      }
    ]
  }'
```

Updated the task definition to use the `secrets` block instead of `environment`:

```json
"secrets": [
  {
    "name": "LITELLM_MASTER_KEY",
    "valueFrom": "<secret-arn>"
  }
]
```

Rotated the exposed key value in Secrets Manager and forced a new ECS deployment to pick up the change:

```bash
aws secretsmanager update-secret \
  --secret-id hiddenlayer-litellm/master-key \
  --secret-string "<new-value>" \
  --region us-east-1

aws ecs update-service \
  --cluster hiddenlayer-litellm-cluster \
  --service hiddenlayer-litellm-service \
  --force-new-deployment \
  --region us-east-1
```

### Key takeaway

ECS differentiates between `environment` and `secrets` in container definitions. Environment values are stored in plaintext and visible across the console, API responses, and any exported task definition JSON. The `secrets` block injects values at container startup from Secrets Manager or SSM Parameter Store and never exposes the plaintext in the task definition itself.

---

## Container image vulnerability scan

The initial Docker image scan reported high vulnerabilities in the base image.

For this implementation, I selected `python:3.11-slim` because it had fewer reported high vulnerabilities than the tested `python:3.11-slim-bookworm` image while keeping the container lightweight and simple for the interview project.

In a production environment, I would continue hardening this image by:
- pinning the base image by digest
- using automated image scanning in CI/CD
- rebuilding regularly as patched images are released
- evaluating distroless or minimal runtime images
- separating build-time and runtime dependencies with a multi-stage build