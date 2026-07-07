# -----------------------------------------------------------------------------
# Managed PostgreSQL 17 HA
# Attached to the data-tier private network. Public access disabled.
# PGBouncer connection pooler configured in transaction mode.
# Automated daily backups and PITR are enabled by default on managed plans.
# DR target zone: de-fra1 (future cross-region replication).
# -----------------------------------------------------------------------------
resource "upcloud_managed_database_postgresql" "main" {
  name  = "ai-finland-pg-${var.environment}"
  title = "ai-finland-pg-${var.environment}"
  plan  = var.pg_plan
  zone  = var.zone

  termination_protection = var.environment == "prod" ? true : false

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
    ip_filter     = ["10.0.1.0/24"]
    node_count    = 2 # Explicit HA: 2-node cluster; plan alone does not guarantee multi-node provisioning

    # PGBouncer connection pooler -- transaction mode for efficient pooling.
    pgbouncer {
      autodb_pool_mode = "transaction"
      autodb_pool_size = 20
    }
  }

  labels = merge(var.tags, {
    Environment = var.environment
  })
}

# -----------------------------------------------------------------------------
# Managed Valkey (Redis-compatible)
# Attached to the data-tier private network. Public access disabled.
# Backup is provider-managed.
# -----------------------------------------------------------------------------
resource "upcloud_managed_database_valkey" "main" {
  name  = "ai-finland-valkey-${var.environment}"
  title = "ai-finland-valkey-${var.environment}"
  plan  = var.valkey_plan
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

  labels = merge(var.tags, {
    Environment = var.environment
  })
}
