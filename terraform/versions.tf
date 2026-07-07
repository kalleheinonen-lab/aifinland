terraform {
  required_version = ">= 1.10" # use_lockfile in s3 backend requires >= 1.10

  required_providers {
    upcloud = {
      source  = "UpCloudLtd/upcloud"
      version = "~> 5.0"
    }
  }
}
