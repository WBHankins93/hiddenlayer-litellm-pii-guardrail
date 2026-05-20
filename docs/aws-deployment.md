# AWS Deployment

This project deploys the Dockerized LiteLLM proxy with a custom PII guardrail to AWS ECS Fargate.

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

## ECR Push

The Docker image is built locally and pushed to Amazon ECR.

```bash
export AWS_REGION=us-east-1
export ECR_REPO=hiddenlayer-litellm-pii-guardrail
export IMAGE_TAG=latest
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

```bash
aws ecr create-repository \
  --repository-name $ECR_REPO \
  --region $AWS_REGION
```

```bash
aws ecr get-login-password --region $AWS_REGION | \
docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
```

```bash
docker tag hiddenlayer-litellm-pii-guardrail:latest \
$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:$IMAGE_TAG
```

```bash
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:$IMAGE_TAG
```

## Notes

The Bedrock quota limitation does not block container deployment. ECS can still validate:

- container startup
- LiteLLM proxy startup
- custom guardrail loading
- `/v1/models` endpoint
- prompt-input PII blocking before Bedrock