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
