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

# ECS Fargate Deployment

## Get default VPC

```bash
export VPC_ID=$(aws ec2 describe-vpcs \
  --filters Name=isDefault,Values=true \
  --query "Vpcs[0].VpcId" \
  --output text)

echo $VPC_ID
```

## Get VPC subnets

```bash
export SUBNETS=$(aws ec2 describe-subnets \
  --filters Name=vpc-id,Values=$VPC_ID \
  --query "Subnets[*].SubnetId" \
  --output text)

echo $SUBNETS
```

## Create ECS security group

```bash
export SG_ID=$(aws ec2 create-security-group \
  --group-name hiddenlayer-litellm-sg \
  --description "Security group for LiteLLM ECS service" \
  --vpc-id $VPC_ID \
  --query GroupId \
  --output text)

echo $SG_ID
```

## Allow inbound traffic on port 4000

```bash
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 4000 \
  --cidr 0.0.0.0/0
```

## Create ECS Fargate service

```bash
aws ecs create-service \
  --cluster $ECS_CLUSTER \
  --service-name $ECS_SERVICE \
  --task-definition $TASK_FAMILY \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={
    subnets=[$(echo $SUBNETS | sed 's/ /,/g')],
    securityGroups=[$SG_ID],
    assignPublicIp=ENABLED
  }" \
  --region $AWS_REGION
```

## List ECS tasks

```bash
aws ecs list-tasks \
  --cluster $ECS_CLUSTER \
  --region $AWS_REGION
```

## Export ECS task ARN

```bash
export TASK_ARN=$(aws ecs list-tasks \
  --cluster $ECS_CLUSTER \
  --query "taskArns[0]" \
  --output text \
  --region $AWS_REGION)

echo $TASK_ARN
```

## Describe ECS task

```bash
aws ecs describe-tasks \
  --cluster $ECS_CLUSTER \
  --tasks $TASK_ARN \
  --region $AWS_REGION
```

---

# Current Deployment Status

The following components have been successfully validated:

- LiteLLM local deployment
- Bedrock model routing
- custom PII guardrail integration
- prompt-input email blocking
- prompt-input SSN blocking
- Docker containerization
- ECR image push
- ECS cluster creation
- ECS Fargate deployment
- ECS task execution role
- CloudWatch logging
- ECS task runtime validation

Current known constraint:

- Bedrock daily quota exhaustion for non-blocked prompts

Remaining validation steps:

- public ECS endpoint testing
- `/v1/models` validation from ECS runtime
- ECS prompt-input validation
- model-output blocking validation
- final presentation preparation