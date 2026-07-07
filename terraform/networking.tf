locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

# -----------------------------------------------------------------------------
# Router -- connects SDN networks and provides the attachment point for the
# NAT gateway. The gateway service injects a service-managed static route;
# it is owned by the UpCloud Network Gateway service, not by us.
# -----------------------------------------------------------------------------
resource "upcloud_router" "main" {
  name = "${local.name_prefix}-router"

  lifecycle {
    ignore_changes = [static_route]
  }
}

# -----------------------------------------------------------------------------
# NAT Gateway -- provides controlled egress for private-only nodes/pods.
# Attached to the router so all networks routed through it gain internet access.
# -----------------------------------------------------------------------------
resource "upcloud_gateway" "nat" {
  name     = "${local.name_prefix}-nat-gw"
  zone     = var.zone
  features = ["nat"]

  router {
    id = upcloud_router.main.id
  }

  labels = var.tags
}

# -----------------------------------------------------------------------------
# Application Network (10.0.1.0/24)
# Used by UKS node groups and application workloads. DHCP default route is
# enabled so traffic egresses via the NAT gateway.
# UKS manages router attachment internally, so we ignore changes to the
# router field.
# -----------------------------------------------------------------------------
resource "upcloud_network" "app" {
  name = "${local.name_prefix}-app-net"
  zone = var.zone

  ip_network {
    address            = "10.0.1.0/24"
    dhcp               = true
    dhcp_default_route = true
    family             = "IPv4"
  }

  # Attach to the router for NAT egress.
  router = upcloud_router.main.id

  # UKS manages router attachment internally; ignore drift on this field.
  lifecycle {
    ignore_changes = [router]
  }
}

# -----------------------------------------------------------------------------
# Data Network (10.0.2.0/24)
# Used by managed services (PostgreSQL, Valkey) which connect via their own
# network block with type='private'. NOT attached to the router -- managed
# services do not need NAT egress.
# -----------------------------------------------------------------------------
resource "upcloud_network" "data" {
  name = "${local.name_prefix}-data-net"
  zone = var.zone

  ip_network {
    address = "10.0.2.0/24"
    dhcp    = true
    family  = "IPv4"
  }
}
