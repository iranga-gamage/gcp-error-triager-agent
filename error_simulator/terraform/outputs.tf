# Terraform outputs for Error Simulator

output "service_url" {
  description = "URL of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.error_simulator.uri
}

output "service_name" {
  description = "Name of the Cloud Run service"
  value       = google_cloud_run_v2_service.error_simulator.name
}

output "service_account_email" {
  description = "Email of the service account used by Cloud Run"
  value       = google_service_account.cloud_run_sa.email
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository name"
  value       = google_artifact_registry_repository.error_simulator_repo.name
}

output "artifact_registry_location" {
  description = "Artifact Registry location"
  value       = google_artifact_registry_repository.error_simulator_repo.location
}

output "docker_image_path" {
  description = "Full path to push Docker images"
  value       = "${var.artifact_registry_location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.error_simulator_repo.repository_id}/error-simulator"
}

output "monitoring_dashboard_url" {
  description = "URL to the Cloud Monitoring dashboard"
  value       = var.enable_monitoring ? "https://console.cloud.google.com/monitoring/dashboards/custom/${google_monitoring_dashboard.error_simulator_dashboard[0].id}?project=${var.project_id}" : "Monitoring not enabled"
}

output "alert_policy_name" {
  description = "Name of the alert policy"
  value       = var.enable_monitoring ? google_monitoring_alert_policy.high_error_rate[0].display_name : "Monitoring not enabled"
}

output "notification_channel_email" {
  description = "Email address for alert notifications"
  value       = var.enable_monitoring ? "iranga.gamage@croud.com" : "Monitoring not enabled"
}

output "pubsub_topic_name" {
  description = "Pub/Sub topic name for alert notifications"
  value       = var.enable_monitoring ? google_pubsub_topic.alert_notifications[0].name : "Monitoring not enabled"
}

output "pubsub_topic_id" {
  description = "Full Pub/Sub topic ID for alert notifications"
  value       = var.enable_monitoring ? google_pubsub_topic.alert_notifications[0].id : "Monitoring not enabled"
}

output "example_curl_commands" {
  description = "Example curl commands to test the service"
  value = {
    health_check       = "curl ${google_cloud_run_v2_service.error_simulator.uri}/"
    list_errors        = "curl ${google_cloud_run_v2_service.error_simulator.uri}/api/v1/errors"
    normal_request     = "curl -X POST ${google_cloud_run_v2_service.error_simulator.uri}/api/v1/analytics"
    trigger_error      = "curl -X POST \"${google_cloud_run_v2_service.error_simulator.uri}/api/v1/analytics?error_type=CALCULATION_ERROR&create_incident=true\""
    date_range_request = "curl -X POST \"${google_cloud_run_v2_service.error_simulator.uri}/api/v1/analytics?date_range=2024-01-01,2024-01-31\""
  }
}
