terraform {
  backend "s3" {
    # Bucket and key are supplied via -backend-config at init time,
    # allowing per-environment state isolation.
    bucket = "ai-finland-tfstate"
    key    = "infrastructure/terraform.tfstate"

    # UpCloud Managed Object Storage region (NOT a compute zone).
    region = "europe-1"

    # UpCloud Managed Object Storage is S3-standard-compatible, not AWS.
    # Skip all AWS-specific preflight checks and use path-style URLs.
    # Native S3 lockfile -- replaces DynamoDB, which UpCloud does not have.
    # Requires Terraform >= 1.10.
    use_lockfile = true

    skip_requesting_account_id  = true
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_region_validation      = true
    skip_s3_checksum            = true
    use_path_style              = true

    # Endpoints are instance-specific -- override via -backend-config.
    # Credentials come from AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
    # (object-storage keys, DISTINCT from UPCLOUD_USERNAME/PASSWORD).
  }
}
