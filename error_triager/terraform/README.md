# Terraform Deployment for GCP Log Collector MCP Server

This directory contains Terraform configuration to deploy the GCP Log Collector MCP Server to Google Cloud Run.

## Prerequisites

1. **Terraform** installed (>= 1.0)
   ```bash
   # Install via Homebrew (macOS)
   brew install terraform

   # Or download from https://www.terraform.io/downloads
   ```

2. **Google Cloud SDK** installed and authenticated
   ```bash
   gcloud auth application-default login
   ```

3. **Required GCP Permissions**
   - `roles/run.admin` (Cloud Run Admin)
   - `roles/iam.serviceAccountAdmin` (Service Account Admin)
   - `roles/iam.serviceAccountUser` (Service Account User)
   - `roles/serviceusage.serviceUsageAdmin` (Service Usage Admin)

## Quick Start

### 1. Create Configuration File

Copy the example configuration and customize it:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and set your values:
```hcl
project_id = "your-gcp-project-id"
region     = "us-central1"
```

### 2. Initialize Terraform

```bash
terraform init
```

This downloads the required provider plugins.

### 3. Review the Plan

```bash
terraform plan
```

This shows what resources will be created.

### 4. Apply the Configuration

```bash
terraform apply
```

Type `yes` to confirm and create the resources.

### 5. Build and Deploy the Container

After Terraform creates the infrastructure, build and deploy your container:

```bash
# From the project root directory (parent of terraform/)
cd ..

# Build and push the container image
gcloud builds submit --tag gcr.io/YOUR-PROJECT-ID/gcp-log-collector-mcp:latest .

# Update the Cloud Run service
cd terraform
terraform apply -var="container_image=gcr.io/YOUR-PROJECT-ID/gcp-log-collector-mcp:latest"
```

## Configuration Options

### Essential Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `project_id` | GCP project ID | - | Yes |
| `region` | GCP region | `us-central1` | No |
| `service_name` | Cloud Run service name | `gcp-log-collector-mcp` | No |

### Scaling Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `min_instances` | Minimum instances (0 for scale-to-zero) | `0` |
| `max_instances` | Maximum instances | `10` |
| `cpu_limit` | CPU limit per instance | `1` |
| `memory_limit` | Memory limit per instance | `512Mi` |
| `cpu_always_allocated` | Keep CPU allocated when idle | `false` |

### Access Control

| Variable | Description | Default |
|----------|-------------|---------|
| `allow_unauthenticated` | Allow public access | `false` |
| `authorized_members` | List of authorized members | `[]` |
| `ingress_mode` | Traffic ingress mode | `INGRESS_TRAFFIC_ALL` |

## Access Control Configuration

### Public Access (Not Recommended for Production)

```hcl
allow_unauthenticated = true
```

### Authenticated Access (Recommended)

```hcl
allow_unauthenticated = false
authorized_members = [
  "user:alice@example.com",
  "serviceAccount:client@project.iam.gserviceaccount.com"
]
```

### Internal VPC Only

```hcl
allow_unauthenticated = false
ingress_mode = "INGRESS_TRAFFIC_INTERNAL_ONLY"
authorized_members = [
  "serviceAccount:internal-sa@project.iam.gserviceaccount.com"
]
```

## Deployment Workflow

### Initial Deployment

```bash
# 1. Initialize and apply infrastructure
terraform init
terraform apply

# 2. Build container
cd ..
gcloud builds submit --tag gcr.io/PROJECT_ID/gcp-log-collector-mcp:latest .

# 3. Update service with container
gcloud run services update gcp-log-collector-mcp \
  --image gcr.io/PROJECT_ID/gcp-log-collector-mcp:latest \
  --region us-central1
```

### Update Deployment

To update the service after code changes:

```bash
# 1. Build new container image
gcloud builds submit --tag gcr.io/PROJECT_ID/gcp-log-collector-mcp:$(git rev-parse --short HEAD) .

# 2. Update Cloud Run service
gcloud run services update gcp-log-collector-mcp \
  --image gcr.io/PROJECT_ID/gcp-log-collector-mcp:$(git rev-parse --short HEAD) \
  --region us-central1
```

### Update Infrastructure

To modify infrastructure settings (scaling, IAM, etc.):

```bash
# Edit terraform.tfvars or pass variables
terraform apply -var="max_instances=20"
```

## Outputs

After deployment, Terraform provides useful outputs:

```bash
terraform output
```

Key outputs:
- `service_url` - Base URL of the Cloud Run service
- `mcp_endpoint` - Full MCP endpoint URL
- `service_account_email` - Service account email
- `build_and_deploy_command` - Commands for building/deploying

To get a specific output:

```bash
terraform output mcp_endpoint
```

## Terraform State Management

### Local State (Development)

By default, Terraform stores state locally in `terraform.tfstate`.

**Important:** Add to `.gitignore`:
```
terraform.tfstate
terraform.tfstate.backup
.terraform/
```

### Remote State (Production)

For production, use remote state storage:

```hcl
# Add to main.tf
terraform {
  backend "gcs" {
    bucket = "your-terraform-state-bucket"
    prefix = "mcp-server/state"
  }
}
```

Create the bucket:
```bash
gsutil mb gs://your-terraform-state-bucket
gsutil versioning set on gs://your-terraform-state-bucket
```

## Troubleshooting

### Permission Denied Errors

Ensure you have the required permissions:
```bash
gcloud projects get-iam-policy YOUR_PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:user:YOUR_EMAIL"
```

### API Not Enabled

If you see "API not enabled" errors:
```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable logging.googleapis.com
```

### Container Image Not Found

The initial deployment uses a placeholder image. After `terraform apply`, you must build and deploy your actual container image:

```bash
cd ..
gcloud builds submit --tag gcr.io/PROJECT_ID/gcp-log-collector-mcp:latest .
```

### Service Account Permissions

If the service can't read logs, verify permissions:
```bash
gcloud projects get-iam-policy YOUR_PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:mcp-log-collector@PROJECT_ID.iam.gserviceaccount.com"
```

## Clean Up

To destroy all resources created by Terraform:

```bash
terraform destroy
```

**Warning:** This will delete:
- Cloud Run service
- Service account
- IAM bindings

Container images in GCR are NOT deleted and must be removed manually if desired:
```bash
gcloud container images delete gcr.io/PROJECT_ID/gcp-log-collector-mcp:latest
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy to Cloud Run
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_CREDENTIALS }}

      - name: Build and push container
        run: |
          gcloud builds submit --tag gcr.io/${{ secrets.GCP_PROJECT_ID }}/gcp-log-collector-mcp:${{ github.sha }}

      - name: Deploy to Cloud Run
        run: |
          gcloud run services update gcp-log-collector-mcp \
            --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/gcp-log-collector-mcp:${{ github.sha }} \
            --region us-central1
```

## Security Best Practices

1. **Use Authenticated Access**: Set `allow_unauthenticated = false`
2. **Restrict Ingress**: Use `INGRESS_TRAFFIC_INTERNAL_ONLY` for internal services
3. **Least Privilege**: Grant only necessary IAM roles
4. **Enable Binary Authorization**: For production workloads
5. **Use Secret Manager**: For sensitive configuration
6. **Enable Audit Logs**: Monitor access and changes
7. **Regular Updates**: Keep dependencies and base images updated

## Cost Optimization

1. **Scale to Zero**: Set `min_instances = 0` for development
2. **Right-size Resources**: Adjust `cpu_limit` and `memory_limit` based on usage
3. **Request Timeout**: Set appropriate `request_timeout` to avoid long-running requests
4. **CPU Allocation**: Use `cpu_always_allocated = false` for scale-to-zero

## Support

For issues or questions:
- Check Cloud Run logs: `gcloud run services logs read gcp-log-collector-mcp`
- Review Terraform docs: https://registry.terraform.io/providers/hashicorp/google/latest/docs
- Cloud Run documentation: https://cloud.google.com/run/docs
