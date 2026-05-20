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

# Environment Variables

```bash
export AWS_REGION=us-east-1
export ECR_REPO=hiddenlayer-litellm-pii-guardrail
export IMAGE_TAG=latest
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

export ECS_CLUSTER=hiddenlayer-litellm-cluster
export ECS_SERVICE=hiddenlayer-litellm-service
export TASK_FAMILY=hiddenlayer-litellm-task
export CONTAINER_NAME=hiddenlayer-litellm
export CONTAINER_PORT=4000
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

## Production Hardening Considerations

For the interview implementation, the ECS Fargate task was exposed with a public IP to keep the deployment focused on the core objective: running LiteLLM with a custom PII guardrail in a container orchestration service.

For a production customer deployment, I would extend this architecture with:

- Application Load Balancer for stable routing
- TLS termination
- Restricted security group ingress
- AWS Secrets Manager for runtime secrets
- CloudWatch alarms for task health and 4xx/5xx spikes
- WAF or API Gateway for additional edge protection
- Private subnets with NAT egress where appropriate
- CI/CD-driven image promotion from ECR to ECS

# Create ECS Cluster

```bash
aws ecs create-cluster \
  --cluster-name $ECS_CLUSTER \
  --region $AWS_REGION
```

---

# Create ECS Task Execution Role

```bash
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": { "Service": "ecs-tasks.amazonaws.com" },
        "Action": "sts:AssumeRole"
      }
    ]
  }'
```

Attach the ECS task execution policy:

```bash
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

---

# ECS Task Definition

Task definitions are stored in:

```txt
deploy/task-definition.json
```

The task definition configures:

- ECS Fargate runtime
- LiteLLM container image
- environment variables
- CloudWatch logging
- exposed container port
- ECS execution role

---

# Create CloudWatch Log Group

```bash
aws logs create-log-group \
  --log-group-name /ecs/hiddenlayer-litellm \
  --region $AWS_REGION
```

---

# Register Task Definition

```bash
aws ecs register-task-definition \
  --cli-input-json file://deploy/task-definition.json \
  --region $AWS_REGION
```

---

# Current Status

At this stage, the following components are validated:

- Docker image build
- ECR image push
- ECS cluster creation
- ECS task definition registration
- LiteLLM container startup locally
- custom guardrail loading
- prompt input PII blocking
- Bedrock model routing

The remaining steps are:

- ECS Fargate service creation
- public endpoint validation
- `/v1/models` validation from ECS
- ECS guardrail validation
- final Bedrock quota re-test