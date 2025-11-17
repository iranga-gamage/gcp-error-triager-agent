variable "project_id" {
  description = "GCP project ID where the resources will be created"
  type        = string
}

variable "region" {
  description = "GCP region for the Cloud Run service"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Name of the Cloud Run service"
  type        = string
  default     = "gcp-log-collector-mcp"
}

variable "service_account_name" {
  description = "Name of the service account for the Cloud Run service"
  type        = string
  default     = "mcp-log-collector"
}

variable "container_image" {
  description = "Container image to deploy (will be updated by Cloud Build)"
  type        = string
  default     = "gcr.io/cloudrun/hello" # Placeholder image for initial deployment
}

variable "min_instances" {
  description = "Minimum number of instances"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum number of instances"
  type        = number
  default     = 10
}

variable "cpu_limit" {
  description = "CPU limit for each container instance"
  type        = string
  default     = "1"
}

variable "memory_limit" {
  description = "Memory limit for each container instance"
  type        = string
  default     = "512Mi"
}

variable "cpu_always_allocated" {
  description = "Whether CPU should be always allocated (true) or only during request processing (false)"
  type        = bool
  default     = false
}

variable "request_timeout" {
  description = "Maximum request timeout in seconds"
  type        = string
  default     = "300s"
}

variable "allow_unauthenticated" {
  description = "Allow unauthenticated access to the service"
  type        = bool
  default     = false
}

variable "authorized_members" {
  description = "List of members authorized to invoke the service (only used if allow_unauthenticated is false)"
  type        = list(string)
  default     = []
  # Examples:
  # ["user:email@example.com", "serviceAccount:sa@project.iam.gserviceaccount.com"]
}

variable "ingress_mode" {
  description = "Ingress traffic mode (INGRESS_TRAFFIC_ALL, INGRESS_TRAFFIC_INTERNAL_ONLY, INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER)"
  type        = string
  default     = "INGRESS_TRAFFIC_ALL"
}

variable "labels" {
  description = "Labels to apply to the Cloud Run service"
  type        = map(string)
  default = {
    application = "mcp-server"
    component   = "log-collector"
  }
}
