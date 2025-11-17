# Terraform configuration for GCP Error Simulator

terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "cloud_run_api" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifact_registry_api" {
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloud_build_api" {
  service            = "cloudbuild.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "monitoring_api" {
  service            = "monitoring.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "logging_api" {
  service            = "logging.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "pubsub_api" {
  service            = "pubsub.googleapis.com"
  disable_on_destroy = false
}

# Create Artifact Registry repository for Docker images
resource "google_artifact_registry_repository" "error_simulator_repo" {
  location      = var.artifact_registry_location
  repository_id = "error-simulator"
  description   = "Docker repository for Error Simulator application"
  format        = "DOCKER"

  depends_on = [google_project_service.artifact_registry_api]
}

# Service Account for Cloud Run
resource "google_service_account" "cloud_run_sa" {
  account_id   = "error-simulator-sa"
  display_name = "Error Simulator Cloud Run Service Account"
  description  = "Service account for Error Simulator Cloud Run service"
}

# Grant necessary permissions to the service account
resource "google_project_iam_member" "monitoring_metric_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_project_iam_member" "logging_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Cloud Run Service
resource "google_cloud_run_v2_service" "error_simulator" {
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.cloud_run_sa.email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    timeout = "${var.timeout_seconds}s"

    containers {
      # Image will be updated via Cloud Build or manual deployment
      image = "${var.artifact_registry_location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.error_simulator_repo.repository_id}/error-simulator:${var.image_tag}"

      ports {
        container_port = var.container_port
      }

      resources {
        limits = {
          cpu    = var.cpu_limit
          memory = var.memory_limit
        }
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "DEBUG"
        value = "false"
      }
    }
  }

  depends_on = [
    google_project_service.cloud_run_api,
    google_artifact_registry_repository.error_simulator_repo,
    google_service_account.cloud_run_sa
  ]

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
    ]
  }
}

# IAM policy to allow unauthenticated access (optional)
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  count = var.allow_unauthenticated ? 1 : 0

  location = google_cloud_run_v2_service.error_simulator.location
  name     = google_cloud_run_v2_service.error_simulator.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Pub/Sub Topic for Alert Notifications
resource "google_pubsub_topic" "alert_notifications" {
  count = var.enable_monitoring ? 1 : 0
  name  = "error-simulator-alerts"

  depends_on = [google_project_service.pubsub_api]
}

# Get project number for Cloud Monitoring service account
data "google_project" "project" {
  project_id = var.project_id
}

# Grant Cloud Monitoring permission to publish to Pub/Sub topic
resource "google_pubsub_topic_iam_member" "monitoring_publisher" {
  count   = var.enable_monitoring ? 1 : 0
  project = var.project_id
  topic   = google_pubsub_topic.alert_notifications[0].name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-monitoring-notification.iam.gserviceaccount.com"

  depends_on = [google_pubsub_topic.alert_notifications]
}

# Email Notification Channel
resource "google_monitoring_notification_channel" "email_notification" {
  count        = var.enable_monitoring ? 1 : 0
  display_name = "Error Simulator Email Notification"
  type         = "email"

  labels = {
    email_address = "iranga.gamage@croud.com"
  }

  enabled = true

  depends_on = [google_project_service.monitoring_api]
}

# Pub/Sub Notification Channel
resource "google_monitoring_notification_channel" "pubsub_notification" {
  count        = var.enable_monitoring ? 1 : 0
  display_name = "Error Simulator Pub/Sub Notification"
  type         = "pubsub"

  labels = {
    topic = google_pubsub_topic.alert_notifications[0].id
  }

  enabled = true

  depends_on = [
    google_project_service.monitoring_api,
    google_pubsub_topic.alert_notifications
  ]
}

# Cloud Monitoring Alert Policy for any error
resource "google_monitoring_alert_policy" "high_error_rate" {
  count        = var.enable_monitoring ? 1 : 0
  display_name = "Error Simulator - Any Error Alert"
  combiner     = "OR"

  conditions {
    display_name = "Any 5xx error detected"

    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND resource.labels.service_name = \"${var.service_name}\" AND metric.type = \"run.googleapis.com/request_count\" AND metric.labels.response_code_class = \"5xx\""
      duration        = "0s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_DELTA"
      }
    }
  }

  notification_channels = var.enable_monitoring ? [
    google_monitoring_notification_channel.email_notification[0].id,
    google_monitoring_notification_channel.pubsub_notification[0].id
  ] : []

  alert_strategy {
    auto_close = "1800s"
  }

  depends_on = [
    google_project_service.monitoring_api,
    google_monitoring_notification_channel.email_notification,
    google_monitoring_notification_channel.pubsub_notification
  ]
}

# Cloud Monitoring Dashboard
resource "google_monitoring_dashboard" "error_simulator_dashboard" {
  count          = var.enable_monitoring ? 1 : 0
  dashboard_json = jsonencode({
    displayName = "Error Simulator Dashboard"
    mosaicLayout = {
      columns = 12
      tiles = [
        {
          width  = 6
          height = 4
          widget = {
            title = "Request Count"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type = \"cloud_run_revision\" AND resource.labels.service_name = \"${var.service_name}\" AND metric.type = \"run.googleapis.com/request_count\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_RATE"
                    }
                  }
                }
              }]
            }
          }
        },
        {
          xPos   = 6
          width  = 6
          height = 4
          widget = {
            title = "Error Rate"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type = \"cloud_run_revision\" AND resource.labels.service_name = \"${var.service_name}\" AND metric.type = \"run.googleapis.com/request_count\" AND metric.labels.response_code_class = \"5xx\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_RATE"
                    }
                  }
                }
              }]
            }
          }
        },
        {
          yPos   = 4
          width  = 6
          height = 4
          widget = {
            title = "Request Latency"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type = \"cloud_run_revision\" AND resource.labels.service_name = \"${var.service_name}\" AND metric.type = \"run.googleapis.com/request_latencies\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_DELTA"
                    }
                  }
                }
              }]
            }
          }
        },
        {
          xPos   = 6
          yPos   = 4
          width  = 6
          height = 4
          widget = {
            title = "Instance Count"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type = \"cloud_run_revision\" AND resource.labels.service_name = \"${var.service_name}\" AND metric.type = \"run.googleapis.com/container/instance_count\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_MAX"
                    }
                  }
                }
              }]
            }
          }
        }
      ]
    }
  })

  depends_on = [google_project_service.monitoring_api]
}
