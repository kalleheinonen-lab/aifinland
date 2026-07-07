# -----------------------------------------------------------------------------
# UKS Kubernetes Cluster
# Private node groups (no public IPs on nodes) with NAT egress via the
# application network's router. Storage encrypted at rest.
# Bootstrap note: cluster starts empty; first CI/CD run deploys workloads.
# HPA handles scaling after initial node_count is established.
# -----------------------------------------------------------------------------
resource "upcloud_kubernetes_cluster" "main" {
  name    = "ai-finland-dev"
  zone    = var.zone
  network = upcloud_network.app.id
  plan    = "production-small"

  # Restrict API server access. Default allows all (dev); restrict in prod.
  control_plane_ip_filter = var.control_plane_ip_filter

  # Nodes have no public IPs; egress is via the NAT gateway on the app network.
  private_node_groups = true

  # At-rest encryption for node storage; no KMS on UpCloud.
  storage_encryption = "data-at-rest"

  labels = var.tags
}

# -----------------------------------------------------------------------------
# Worker node group -- general application workloads
# -----------------------------------------------------------------------------
resource "upcloud_kubernetes_node_group" "workers" {
  cluster    = upcloud_kubernetes_cluster.main.id
  name       = "workers"
  plan       = "4xCPU-8GB"
  node_count = 3

  # Best-effort spread across physical hosts for resilience.
  anti_affinity = true

  labels = {
    role = "worker"
    env  = var.environment
  }
}

# -----------------------------------------------------------------------------
# Observability node group -- Prometheus, Grafana, Loki, OTel Collector
# Isolated from worker nodes so monitoring survives application pressure.
# -----------------------------------------------------------------------------
resource "upcloud_kubernetes_node_group" "observability" {
  cluster    = upcloud_kubernetes_cluster.main.id
  name       = "observability"
  plan       = "2xCPU-4GB"
  node_count = 2

  labels = {
    role = "observability"
  }
}
