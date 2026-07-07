# -----------------------------------------------------------------------------
# Managed Load Balancer
# Public ingress terminates here; backend traffic flows over the private
# application network. WAF and TLS config are added once certificates exist
# (see Principle A: bootstrap vs steady-state).
# maintenance_dow/time: Saturday 03:00 UTC to minimise user impact.
# -----------------------------------------------------------------------------
resource "upcloud_loadbalancer" "main" {
  name              = "${local.name_prefix}-lb"
  plan              = "production-small"
  zone              = var.zone
  configured_status = "started"

  # Private network attachment -- backend traffic stays on the SDN.
  networks {
    name    = "private"
    type    = "private"
    family  = "IPv4"
    network = upcloud_network.app.id
  }

  # Public network attachment -- internet-facing ingress.
  networks {
    name   = "public"
    type   = "public"
    family = "IPv4"
  }

  maintenance_dow  = "saturday"
  maintenance_time = "03:00:00Z"

  labels = var.tags
}
