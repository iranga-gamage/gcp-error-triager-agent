terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "run_api" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloudbuild_api" {
  service            = "cloudbuild.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "logging_api" {
  service            = "logging.googleapis.com"
  disable_on_destroy = false
}

# Service account for the Cloud Run service
resource "google_service_account" "mcp_server" {
  account_id   = var.service_account_name
  display_name = "MCP Log Collector Service Account"
  description  = "Service account for GCP Log Collector MCP Server"
}

# Grant logging viewer permissions to the service account
resource "google_project_iam_member" "logging_viewer" {
  project = var.project_id
  role    = "roles/logging.viewer"
  member  = "serviceAccount:${google_service_account.mcp_server.email}"
}

# Grant logging private log viewer permissions (for all log types)
resource "google_project_iam_member" "logging_private_viewer" {
  project = var.project_id
  role    = "roles/logging.privateLogViewer"
  member  = "serviceAccount:${google_service_account.mcp_server.email}"
}

# Build and deploy the Cloud Run service
resource "google_cloud_run_v2_service" "mcp_server" {
  name     = var.service_name
  location = var.region
  ingress  = var.ingress_mode

  depends_on = [
    google_project_service.run_api,
    google_project_service.cloudbuild_api
  ]

  template {
    service_account = google_service_account.mcp_server.email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      # This will be updated after initial deployment with Cloud Build
      image = var.container_image

      ports {
        container_port = 8080
      }

      # Resource limits
      resources {
        limits = {
          cpu    = var.cpu_limit
          memory = var.memory_limit
        }
        cpu_idle = var.cpu_always_allocated
      }

      # Startup probe
      startup_probe {
        http_get {
          path = "/mcp"
          port = 8080
        }
        initial_delay_seconds = 5
        timeout_seconds       = 5
        period_seconds        = 10
        failure_threshold     = 3
      }

      # Liveness probe
      liveness_probe {
        http_get {
          path = "/mcp"
          port = 8080
        }
        initial_delay_seconds = 30
        timeout_seconds       = 5
        period_seconds        = 30
        failure_threshold     = 3
      }
    }

    timeout = var.request_timeout
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  lifecycle {
    ignore_changes = [
      # Ignore changes to the image since it will be updated by CI/CD
      template[0].containers[0].image,
    ]
  }
}

# IAM policy to allow public or authenticated access
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  count = var.allow_unauthenticated ? 1 : 0

  name     = google_cloud_run_v2_service.mcp_server.name
  location = google_cloud_run_v2_service.mcp_server.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# For authenticated access, grant specific users/service accounts
resource "google_cloud_run_v2_service_iam_member" "authenticated_access" {
  for_each = var.allow_unauthenticated ? [] : toset(var.authorized_members)

  name     = google_cloud_run_v2_service.mcp_server.name
  location = google_cloud_run_v2_service.mcp_server.location
  role     = "roles/run.invoker"
  member   = each.value
}
