variable "environment" {
  description = "Deployment environment name"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "stg", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, stg, staging, prod."
  }
}

variable "project_name" {
  description = "Project identifier used in resource naming"
  type        = string
  default     = "ai-finland"
}

variable "zone" {
  description = "UpCloud zone for resource deployment"
  type        = string
  default     = "fi-hel1"
}

variable "tags" {
  description = "Common resource labels applied to all infrastructure"
  type        = map(string)
  default = {
    Owner              = "ai-finland-platform-team"
    Application        = "ai-finland-matchmaking"
    ManagedBy          = "terraform"
    DataClassification = "confidential"
  }
}

variable "control_plane_ip_filter" {
  description = "CIDR ranges allowed to reach the UKS API server. Default allows all (dev). Restrict to admin/CI CIDRs in prod."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "pg_plan" {
  description = "Managed PostgreSQL plan size"
  type        = string
  default     = "2x2xCPU-4GB-50GB"
}

variable "valkey_plan" {
  description = "Managed Valkey plan size"
  type        = string
  default     = "1x1xCPU-2GB"
}

variable "worker_node_count" {
  description = "Number of worker nodes in the UKS cluster"
  type        = number
  default     = 3
}
