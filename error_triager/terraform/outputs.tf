output "service_url" {
  description = "URL of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.mcp_server.uri
}

output "mcp_endpoint" {
  description = "MCP endpoint URL"
  value       = "${google_cloud_run_v2_service.mcp_server.uri}/mcp"
}

output "service_name" {
  description = "Name of the Cloud Run service"
  value       = google_cloud_run_v2_service.mcp_server.name
}

output "service_account_email" {
  description = "Email of the service account used by the Cloud Run service"
  value       = google_service_account.mcp_server.email
}

output "region" {
  description = "Region where the service is deployed"
  value       = google_cloud_run_v2_service.mcp_server.location
}

output "project_id" {
  description = "GCP project ID"
  value       = var.project_id
}

output "container_image_placeholder" {
  description = "Placeholder for the container image (update this with your actual image)"
  value       = "gcr.io/${var.project_id}/${var.service_name}:latest"
}

output "build_and_deploy_command" {
  description = "Command to build and deploy the container"
  value       = <<-EOT
    # Build and deploy the container image:
    gcloud builds submit --tag gcr.io/${var.project_id}/${var.service_name}:latest ..

    # Update the Cloud Run service with the new image:
    gcloud run services update ${var.service_name} \
      --image gcr.io/${var.project_id}/${var.service_name}:latest \
      --region ${var.region} \
      --project ${var.project_id}
  EOT
}
