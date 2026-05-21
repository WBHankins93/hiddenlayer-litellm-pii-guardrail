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

## Prerequisites

Before deployment, ensure:

- AWS CLI is installed and authenticated
- Docker Desktop is running
- the LiteLLM container image builds locally
- AWS Bedrock access is enabled for the target model

## Configure Environment Variables

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

## Create ECR Repository

The Docker image is built locally and pushed to Amazon ECR.

```bash
aws ecr create-repository \
  --repository-name $ECR_REPO \
  --region $AWS_REGION
```

## Authenticate Docker to ECR

```bash
aws ecr get-login-password --region $AWS_REGION | \
docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
```

## Tag Docker Image

```bash
docker tag hiddenlayer-litellm-pii-guardrail:latest \
$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:$IMAGE_TAG
```

## Push Docker Image to ECR

```bash
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:$IMAGE_TAG
```

## Create ECS Cluster

```bash
aws ecs create-cluster \
  --cluster-name $ECS_CLUSTER \
  --region $AWS_REGION
```

## Create ECS Task Execution Role

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

## Attach ECS Task Execution Policy

```bash
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

## ECS Task Definition

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

## Create CloudWatch Log Group

```bash
aws logs create-log-group \
  --log-group-name /ecs/hiddenlayer-litellm \
  --region $AWS_REGION
```

## Register Task Definition

```bash
aws ecs register-task-definition \
  --cli-input-json file://deploy/task-definition.json \
  --region $AWS_REGION
```

## ECS Runtime IAM Configuration

The ECS task requires a runtime task role to access Amazon Bedrock.

The ECS execution role only:
- pulls images from ECR
- writes logs to CloudWatch

The runtime application permissions are provided separately using:

```json
"taskRoleArn"
```

Without this role, Bedrock requests fail with:

```txt
Unable to locate credentials
```

## ECS Fargate Deployment

### Get Default VPC

```bash
export VPC_ID=$(aws ec2 describe-vpcs \
  --filters Name=isDefault,Values=true \
  --query "Vpcs[0].VpcId" \
  --output text)

echo $VPC_ID
```

### Get VPC Subnets

```bash
export SUBNETS=$(aws ec2 describe-subnets \
  --filters Name=vpc-id,Values=$VPC_ID \
  --query "Subnets[*].SubnetId" \
  --output text)

echo $SUBNETS
```

### Create ECS Security Group

```bash
export SG_ID=$(aws ec2 create-security-group \
  --group-name hiddenlayer-litellm-sg \
  --description "Security group for LiteLLM ECS service" \
  --vpc-id $VPC_ID \
  --query GroupId \
  --output text)

echo $SG_ID
```

### Allow Inbound Traffic on Port 4000

```bash
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 4000 \
  --cidr 0.0.0.0/0
```

### Create ECS Fargate Service

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

### List ECS Tasks

```bash
aws ecs list-tasks \
  --cluster $ECS_CLUSTER \
  --region $AWS_REGION
```

### Export ECS Task ARN

```bash
export TASK_ARN=$(aws ecs list-tasks \
  --cluster $ECS_CLUSTER \
  --query "taskArns[0]" \
  --output text \
  --region $AWS_REGION)

echo $TASK_ARN
```

### Describe ECS Task

```bash
aws ecs describe-tasks \
  --cluster $ECS_CLUSTER \
  --tasks $TASK_ARN \
  --region $AWS_REGION
```

## Validate ECS Deployment

Retrieve the ECS public IP and validate the deployment:

```bash
export BASE_URL=http://<public-ip>:4000
export LITELLM_MASTER_KEY=bh-hiddenlayer-demo

./examples/curl_examples.sh
```

Validated successfully:
- LiteLLM proxy startup
- ECS Fargate deployment
- Bedrock authentication
- custom guardrail loading
- email blocking
- SSN blocking
- `/v1/models` endpoint

Safe prompts currently return a Bedrock quota response:

```txt
Too many tokens per day, please wait before trying again.
```

This confirms the ECS runtime and Bedrock integration are functioning correctly.

## Production Considerations

This implementation intentionally deploys ECS Fargate with a public IP to keep the interview scope focused on the core deployment and guardrail integration.

For production deployments, recommended improvements include:

- Application Load Balancer
- TLS termination
- restricted security group ingress
- AWS Secrets Manager
- CloudWatch alarms
- private subnets
- CI/CD deployment pipeline