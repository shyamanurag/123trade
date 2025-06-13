#!/bin/bash

# Exit on error
set -e

# Configuration
APP_NAME="algo-scalper"
REGION="us-east-1"
VPC_CIDR="10.0.0.0/16"
DB_INSTANCE_CLASS="db.t3.micro"
REDIS_NODE_TYPE="cache.t3.micro"
S3_BUCKET_NAME="${APP_NAME}-static-$(date +%s)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "Starting AWS infrastructure setup for ${APP_NAME}..."

# Create VPC
echo "Creating VPC..."
VPC_ID=$(aws ec2 create-vpc \
    --cidr-block ${VPC_CIDR} \
    --query 'Vpc.VpcId' \
    --output text)

aws ec2 create-tags --resources ${VPC_ID} --tags Key=Name,Value=${APP_NAME}-vpc
aws ec2 modify-vpc-attribute --vpc-id ${VPC_ID} --enable-dns-hostnames
aws ec2 modify-vpc-attribute --vpc-id ${VPC_ID} --enable-dns-support

# Create ECR repository
echo "Creating ECR repository..."
aws ecr create-repository \
    --repository-name ${APP_NAME} \
    --image-scanning-configuration scanOnPush=true

# Create RDS instance
echo "Creating RDS instance..."
DB_INSTANCE_ID=$(aws rds create-db-instance \
    --db-instance-identifier ${APP_NAME}-db \
    --db-instance-class ${DB_INSTANCE_CLASS} \
    --engine postgres \
    --allocated-storage 20 \
    --master-username admin \
    --master-user-password ${DB_PASSWORD} \
    --vpc-security-group-ids ${DB_SECURITY_GROUP_ID} \
    --db-subnet-group-name ${APP_NAME}-db-subnet-group \
    --query 'DBInstance.DBInstanceIdentifier' \
    --output text)

# Create ElastiCache cluster
echo "Creating ElastiCache cluster..."
aws elasticache create-cache-cluster \
    --cache-cluster-id ${APP_NAME}-redis \
    --cache-node-type ${REDIS_NODE_TYPE} \
    --engine redis \
    --num-cache-nodes 1 \
    --vpc-security-group-ids ${REDIS_SECURITY_GROUP_ID} \
    --subnet-group-name ${APP_NAME}-redis-subnet-group

# Create S3 bucket
echo "Creating S3 bucket..."
aws s3api create-bucket \
    --bucket ${S3_BUCKET_NAME} \
    --region ${REGION} \
    --create-bucket-configuration LocationConstraint=${REGION}

# Configure S3 bucket for static website hosting
aws s3api put-bucket-website \
    --bucket ${S3_BUCKET_NAME} \
    --website-configuration '{
        "IndexDocument": {"Suffix": "index.html"},
        "ErrorDocument": {"Key": "error.html"}
    }'

# Create CloudFront distribution
echo "Creating CloudFront distribution..."
DISTRIBUTION_ID=$(aws cloudfront create-distribution \
    --origin-domain-name ${S3_BUCKET_NAME}.s3.amazonaws.com \
    --query 'Distribution.Id' \
    --output text)

# Create ECS cluster
echo "Creating ECS cluster..."
aws ecs create-cluster \
    --cluster-name ${APP_NAME}-cluster

# Create ECS task definition
echo "Creating ECS task definition..."
aws ecs register-task-definition \
    --cli-input-json file://task-definition.json

# Create ECS service
echo "Creating ECS service..."
aws ecs create-service \
    --cluster ${APP_NAME}-cluster \
    --service-name ${APP_NAME}-service \
    --task-definition ${APP_NAME}:1 \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_IDS}],securityGroups=[${ECS_SECURITY_GROUP_ID}],assignPublicIp=ENABLED}"

echo -e "${GREEN}AWS infrastructure setup completed successfully!${NC}"

# Output configuration values
echo "Please add these values to your GitHub repository secrets:"
echo "AWS_ACCESS_KEY_ID: Your AWS access key"
echo "AWS_SECRET_ACCESS_KEY: Your AWS secret key"
echo "AWS_REGION: ${REGION}"
echo "ECS_CLUSTER: ${APP_NAME}-cluster"
echo "ECS_SERVICE: ${APP_NAME}-service"
echo "AWS_S3_BUCKET: ${S3_BUCKET_NAME}"
echo "CLOUDFRONT_DISTRIBUTION_ID: ${DISTRIBUTION_ID}" 