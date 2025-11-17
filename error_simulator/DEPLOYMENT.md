# Deployment Guide - GCP Error Simulator

This guide covers deploying the Error Simulator application to Google Cloud Run using Terraform.

## Prerequisites

1. **GCP Account**: Active Google Cloud Platform account
2. **GCP Project**: A GCP project with billing enabled
3. **Tools Installed**:
   - [gcloud CLI](https://cloud.google.com/sdk/docs/install) (authenticated)
   - [Terraform](https://www.terraform.io/downloads) >= 1.0
   - [Docker](https://docs.docker.com/get-docker/)
   - [uv](https://github.com/astral-sh/uv) for Python package management

## Step 1: Authenticate with GCP

```bash
# Login to GCP
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Configure Docker authentication for Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev
```

## Step 2: Configure Terraform Variables

```bash
cd terraform

# Copy example variables file
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your values
# Required: Update project_id to your GCP project ID
vim terraform.tfvars
```

Example `terraform.tfvars`:
```hcl
project_id = "my-gcp-project"
region     = "us-central1"
```

## Step 3: Initialize Terraform

```bash
# Initialize Terraform (downloads providers)
terraform init

# Review the deployment plan
terraform plan
```

## Step 4: Deploy Infrastructure

```bash
# Apply Terraform configuration
terraform apply

# Review the changes and type 'yes' to confirm
```

This will create:
- Artifact Registry repository
- Cloud Run service (initial placeholder)
- Service account with necessary permissions
- IAM bindings
- Monitoring alert policy
- Monitoring dashboard

## Step 5: Build and Push Docker Image

```bash
# Return to project root
cd ..

# Set variables
export PROJECT_ID=$(terraform -chdir=terraform output -raw service_name | cut -d'/' -f1)
export REGION="us-central1"
export IMAGE_NAME="error-simulator"

# Get the full image path from Terraform output
export IMAGE_PATH=$(terraform -chdir=terraform output -raw docker_image_path)

# Build the Docker image
docker build -t ${IMAGE_PATH}:latest .

# Push to Artifact Registry
docker push ${IMAGE_PATH}:latest
```

**Alternative: Use Cloud Build** (recommended for production):
```bash
# Submit build to Cloud Build
gcloud builds submit --tag ${IMAGE_PATH}:latest .
```

## Step 6: Deploy to Cloud Run

```bash
# Deploy the new image to Cloud Run
gcloud run deploy error-simulator \
  --image ${IMAGE_PATH}:latest \
  --region ${REGION} \
  --platform managed
```

Or update Terraform to trigger redeployment:
```bash
cd terraform
terraform apply -var="image_tag=$(date +%s)"
```

## Step 7: Verify Deployment

```bash
# Get the service URL
terraform output service_url

# Test health check
curl $(terraform output -raw service_url)/

# List available error types
curl $(terraform output -raw service_url)/api/v1/errors

# Test analytics endpoint
curl -X POST $(terraform output -raw service_url)/api/v1/analytics
```

## Step 8: Test Error Simulation

```bash
# Trigger a calculation error with incident creation
curl -X POST "$(terraform output -raw service_url)/api/v1/analytics?error_type=CALCULATION_ERROR&create_incident=true"

# Trigger a data validation error
curl -X POST "$(terraform output -raw service_url)/api/v1/analytics?error_type=INVALID_DATA&create_incident=true"

# Request analytics with date range
curl -X POST "$(terraform output -raw service_url)/api/v1/analytics?date_range=2024-01-01,2024-01-31"
```

## Viewing Logs and Incidents

### Cloud Logging
```bash
# View logs in Cloud Console
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=error-simulator" --limit 50 --format json
```

Or visit: https://console.cloud.google.com/logs

### Cloud Monitoring

View the monitoring dashboard:
```bash
terraform output monitoring_dashboard_url
```

Or visit: https://console.cloud.google.com/monitoring

### Incidents

Incidents are logged as structured JSON in Cloud Logging. Search for:
```
INCIDENT_CREATED
```

## Updating the Application

### Code Changes

```bash
# Make your code changes
# ...

# Rebuild and push image
docker build -t ${IMAGE_PATH}:$(date +%s) .
docker push ${IMAGE_PATH}:$(date +%s)

# Deploy to Cloud Run
gcloud run services update error-simulator \
  --image ${IMAGE_PATH}:$(date +%s) \
  --region ${REGION}
```

### Infrastructure Changes

```bash
cd terraform

# Make changes to .tf files
# ...

# Review changes
terraform plan

# Apply changes
terraform apply
```

## Cleanup

To remove all resources:

```bash
cd terraform

# Destroy all resources
terraform destroy

# Type 'yes' to confirm
```

**Note**: This will delete:
- Cloud Run service
- Artifact Registry repository (and all images)
- Service account
- Monitoring resources

## Troubleshooting

### Build Failures

**Issue**: Docker build fails
```bash
# Check Docker is running
docker ps

# Verify Dockerfile syntax
docker build --no-cache -t test .
```

**Issue**: Push to Artifact Registry fails
```bash
# Re-authenticate Docker
gcloud auth configure-docker us-central1-docker.pkg.dev

# Verify repository exists
gcloud artifacts repositories list --location=us-central1
```

### Deployment Failures

**Issue**: Terraform apply fails with API not enabled
```bash
# Manually enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable monitoring.googleapis.com
```

**Issue**: Cloud Run service won't start
```bash
# Check logs
gcloud run services logs read error-simulator --region=us-central1

# Verify image exists
gcloud artifacts docker images list ${IMAGE_PATH}
```

### Application Errors

**Issue**: 500 errors on requests
```bash
# Check application logs
gcloud logging read "resource.type=cloud_run_revision" --limit 100

# Test locally
docker run -p 8080:8080 -e GCP_PROJECT_ID=test-project ${IMAGE_PATH}:latest
curl http://localhost:8080/api/v1/analytics
```

## Security Considerations

1. **Authentication**: By default, `allow_unauthenticated = true`. For production:
   ```hcl
   # In terraform.tfvars
   allow_unauthenticated = false
   ```

2. **Service Account**: Minimum required permissions are granted. Review IAM roles:
   - `roles/monitoring.metricWriter`
   - `roles/logging.logWriter`

3. **Network**: Consider using VPC Service Controls for additional security

4. **Secrets**: Never commit `terraform.tfvars` or credentials to version control

## Cost Optimization

1. **Minimum Instances**: Set to 0 to avoid charges when idle
2. **Memory/CPU**: Adjust based on actual usage patterns
3. **Log Retention**: Configure log retention policies
4. **Monitoring**: Review monitoring costs and adjust alert frequency

## Production Checklist

- [ ] Set `allow_unauthenticated = false`
- [ ] Configure proper IAM roles
- [ ] Set up alerting notifications
- [ ] Configure log retention policies
- [ ] Enable VPC Service Controls (if needed)
- [ ] Set up CI/CD pipeline
- [ ] Configure custom domain
- [ ] Enable Cloud Armor (if needed)
- [ ] Set up backup/disaster recovery
- [ ] Document runbook procedures
