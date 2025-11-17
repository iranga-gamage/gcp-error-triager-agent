#!/bin/bash
set -e

# Simple deployment script
# Reads config from Terraform and deploys the container

cd terraform

# Get config from Terraform
PROJECT_ID=$(terraform output -raw project_id)
REGION=$(terraform output -raw region)
SERVICE_NAME=$(terraform output -raw service_name)

cd ..

# Use git commit hash as tag, or 'latest'
TAG=${1:-$(git rev-parse --short HEAD 2>/dev/null || echo "latest")}

IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${TAG}"

echo "Building and deploying ${IMAGE}..."

# Build container
gcloud builds submit --tag="${IMAGE}" --project="${PROJECT_ID}" .

# Update Terraform with new image
cd terraform
terraform apply -auto-approve -var="container_image=${IMAGE}"

echo ""
echo "Deployed: $(terraform output -raw mcp_endpoint)"
