# Cloud Run Deployment Guide

This guide explains how to deploy the GCP Log Collector MCP Server to Google Cloud Run.

## Deployment Options

Choose your preferred deployment method:

1. **Terraform (Recommended for Production)** - Infrastructure as Code approach
   - See [terraform/README.md](terraform/README.md) for detailed instructions
   - Provides reproducible infrastructure
   - Easy to version control and manage changes
   - Quick start: `cd terraform && terraform init && terraform apply`

2. **Manual Deployment (Quick Start)** - Use gcloud CLI directly
   - See instructions below
   - Good for testing and development
   - Quick one-command deployment

3. **Deployment Script** - Automated build and deploy
   - Use `./deploy.sh --project YOUR_PROJECT_ID`
   - Handles both building and deploying
   - Works with or without Terraform

## Prerequisites

- Google Cloud SDK (`gcloud`) installed and configured
- Docker installed (optional, for local testing)
- A GCP project with Cloud Run API enabled
- Appropriate IAM permissions to deploy Cloud Run services

## Manual Deployment Steps

### 1. Set Environment Variables

```bash
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"  # or your preferred region
export SERVICE_NAME="gcp-log-collector-mcp"
```

### 2. Build and Deploy to Cloud Run

You can deploy directly from source using Cloud Build:

```bash
gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $REGION \
  --project $PROJECT_ID \
  --platform managed \
  --allow-unauthenticated
```

### 3. Alternative: Build Docker Image Locally

If you prefer to build the image locally:

```bash
# Build the Docker image
docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME:latest .

# Push to Google Container Registry
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:latest

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
  --region $REGION \
  --project $PROJECT_ID \
  --platform managed \
  --allow-unauthenticated
```

## Testing Locally

To test the server locally before deployment:

```bash
# Run the server
uv run python src/gcp_logs_mcp_server.py

# Or using Docker
docker build -t gcp-log-collector-mcp .
docker run -p 8080:8080 \
  -e PORT=8080 \
  -v ~/.config/gcloud:/root/.config/gcloud \
  gcp-log-collector-mcp
```

The server will be available at `http://localhost:8080`.

## Authentication

The MCP server needs GCP credentials to access Cloud Logging. For Cloud Run deployment:

### Option 1: Service Account (Recommended)

1. Create a service account with appropriate permissions:
   ```bash
   gcloud iam service-accounts create mcp-log-collector \
     --display-name="MCP Log Collector Service Account"
   ```

2. Grant necessary permissions:
   ```bash
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:mcp-log-collector@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/logging.viewer"
   ```

3. Deploy with the service account:
   ```bash
   gcloud run deploy $SERVICE_NAME \
     --source . \
     --region $REGION \
     --project $PROJECT_ID \
     --platform managed \
     --service-account=mcp-log-collector@$PROJECT_ID.iam.gserviceaccount.com \
     --allow-unauthenticated
   ```

### Option 2: Workload Identity (For Production)

For production deployments, use Workload Identity to securely manage credentials.

## Configuration

The server accepts the following environment variables:

- `PORT`: The port to listen on (default: 8080)

Set environment variables during deployment:

```bash
gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $REGION \
  --project $PROJECT_ID \
  --set-env-vars PORT=8080
```

## Using the MCP Server

Once deployed, you can use the MCP server with any MCP client. The server exposes one tool:

### `collect_gcp_logs`

Collects GCP logs for a specific resource and time range.

**Parameters:**
- `project_id` (string, required): GCP project ID to query logs from
- `resource_type` (string, required): GCP resource type (e.g., 'cloud_run_revision', 'gce_instance')
- `resource_labels` (object, required): Dictionary of resource labels to filter by
- `start_time` (string, required): Start timestamp in ISO 8601 format
- `end_time` (string, required): End timestamp in ISO 8601 format
- `include_all_severities` (boolean, optional): Include all severity levels (default: true)
- `max_entries` (integer, optional): Maximum number of log entries (default: 10000)

## Monitoring

View logs for your deployed service:

```bash
gcloud run services logs read $SERVICE_NAME \
  --region $REGION \
  --project $PROJECT_ID
```

## Troubleshooting

### Server won't start
- Check Cloud Run logs for error messages
- Verify the service account has appropriate permissions
- Ensure the PORT environment variable is set correctly

### Authentication errors
- Verify the service account has `roles/logging.viewer` permission
- Check that the service account is attached to the Cloud Run service

### Timeout errors
- Increase Cloud Run timeout: `--timeout=300s`
- Consider adjusting `max_entries` parameter to fetch fewer logs

## Cost Considerations

- Cloud Run charges for CPU and memory usage
- Cloud Logging API has quotas and may incur costs for large log volumes
- Consider setting appropriate `max_entries` limits to control costs

## Security Best Practices

1. Use a dedicated service account with minimal permissions
2. Enable authentication for the Cloud Run service in production
3. Use VPC Service Controls to restrict access
4. Regularly audit service account permissions
5. Monitor API usage and set up billing alerts

## Next Steps

- Configure authentication for production use
- Set up monitoring and alerting
- Integrate with your MCP client application
- Consider implementing rate limiting for production workloads
