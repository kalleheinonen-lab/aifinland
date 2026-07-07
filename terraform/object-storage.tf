# -----------------------------------------------------------------------------
# Managed Object Storage (S3-standard-compatible)
# Attached to the data-tier private network. No public network attached.
# Buckets are private by default; serve public content via presigned URLs.
# Object versioning is provider-managed.
# DR target zone: de-fra1 (future cross-region replication).
# -----------------------------------------------------------------------------
resource "upcloud_managed_object_storage" "main" {
  name              = "ai-finland-objsto-dev"
  region            = "europe-1"
  configured_status = "started"

  # Attach to the data-tier private network.
  network {
    family = "IPv4"
    name   = "objsto-private"
    type   = "private"
    uuid   = upcloud_network.data.id
  }

  labels = var.tags
}

# -----------------------------------------------------------------------------
# Object Storage service account user
# Access keys are created separately and delivered to the app via Vault/OpenBao.
# -----------------------------------------------------------------------------
resource "upcloud_managed_object_storage_user" "app" {
  service_uuid = upcloud_managed_object_storage.main.id
  username     = "app-service-account"
}
