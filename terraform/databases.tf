# -----------------------------------------------------------------------------
# Managed PostgreSQL 17 HA
# Attached to the data-tier private network. Public access disabled.
# PGBouncer connection pooler configured in transaction mode.
# Automated daily backups and PITR are enabled by default on managed plans.
# DR target zone: de-fra1 (future cross-region replication).
# -----------------------------------------------------------------------------
resource "upcloud_managed_database_postgresql" "main" {
  name  = "ai-finland-pg-dev"
  title = "ai-finland-pg-dev"
  plan  = "2x2xCPU-4GB-50GB"
  zone  = var.zone

  maintenance_window_dow  = "sunday"
  maintenance_window_time = "03:00:00"

  # Attach to the data-tier private network -- no public IP.
  network {
    family = "IPv4"
    name   = "pg-private"
    type   = "private"
    uuid   = upcloud_network.data.id
  }

  properties {
    version       = "17"
    public_access = false
    timezone      = "Europe/Helsinki"
    ip_filter     = ["10.0.1.0/24", "10.0.2.0/24"]

    # PGBouncer connection pooler -- transaction mode for efficient pooling.
    pgbouncer {
      autodb_pool_mode = "transaction"
      autodb_pool_size = 20
    }
  }

  labels = var.tags
}

# -----------------------------------------------------------------------------
# Managed Valkey (Redis-compatible)
# Attached to the data-tier private network. Public access disabled.
# Backup is provider-managed.
# -----------------------------------------------------------------------------
resource "upcloud_managed_database_valkey" "main" {
  name  = "ai-finland-valkey-dev"
  title = "ai-finland-valkey-dev"
  plan  = "1x1xCPU-2GB"
  zone  = var.zone

  # Attach to the data-tier private network -- no public IP.
  network {
    family = "IPv4"
    name   = "valkey-private"
    type   = "private"
    uuid   = upcloud_network.data.id
  }

  properties {
    public_access = false
  }

  labels = var.tags
}
