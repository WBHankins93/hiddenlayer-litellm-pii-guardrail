# ECS Fargate Deployment Notes

This project deploys the Dockerized LiteLLM proxy to AWS ECS Fargate.

## Deployment Goal

Run the same containerized LiteLLM proxy validated locally inside AWS using ECS Fargate.

## Deployment Flow

```txt
Local Docker Image
    ↓
Amazon ECR
    ↓
ECS Task Definition
    ↓
ECS Fargate Service
    ↓
LiteLLM Proxy
    ↓
Custom PII Guardrail
    ↓
Amazon Bedrock
```

## Validation Targets

After deployment, validate:

- ECS task reaches `RUNNING`
- CloudWatch logs show LiteLLM startup
- `/v1/models` returns configured Bedrock model
- prompt input containing email is blocked
- prompt input containing SSN is blocked
- safe prompt reaches Bedrock when quota is available

## Known Constraint

During implementation, Bedrock returned a daily token quota limit for safe prompts. This does not block ECS validation because PII-blocked prompts are intercepted before the Bedrock call.

## Operational Notes

### AWS CLI Credential Issue

During ECR setup, the AWS CLI returned:

```txt
InvalidClientTokenId
```

The issue was isolated to local AWS CLI credentials, not the LiteLLM runtime itself.

Resolution:
- refreshed AWS CLI credentials
- validated identity using:

```bash
aws sts get-caller-identity
```

### Bedrock Quota Constraint

Bedrock returned:

```txt
Too many tokens per day, please wait before trying again.
```

This did not block deployment progress because:
- prompt-input PII blocking occurs before the Bedrock call
- Docker validation remained fully testable
- ECS deployment path remained valid

### Docker Build Context Issue

Initial Docker builds failed because the Dockerfile was executed from the `deploy/` directory while attempting to copy files from the repository root.

Resolution:
- moved build execution to repository root
- used repository root as Docker build context

### Current Deployment Strategy

Initial ECS deployment uses:
- ECS Fargate
- public IP assignment
- no ALB

This was intentionally selected to:
- reduce deployment complexity
- validate the orchestration path quickly
- focus on the interview project objectives

Production hardening improvements are documented separately.