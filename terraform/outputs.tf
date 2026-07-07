output "app_network_id" {
  description = "ID of the application-tier SDN network"
  value       = upcloud_network.app.id
}

output "data_network_id" {
  description = "ID of the data-tier SDN network"
  value       = upcloud_network.data.id
}

output "router_id" {
  description = "ID of the SDN router connecting networks to the NAT gateway"
  value       = upcloud_router.main.id
}

output "gateway_id" {
  description = "ID of the NAT gateway providing controlled egress"
  value       = upcloud_gateway.nat.id
}

# -----------------------------------------------------------------------------
# PostgreSQL outputs
# DR note: de-fra1 is the target zone for future cross-region replication.
# -----------------------------------------------------------------------------
output "pg_service_uri" {
  description = "PostgreSQL service URI (includes credentials -- handle as a secret)"
  value       = upcloud_managed_database_postgresql.main.service_uri
  sensitive   = true
}

output "pg_host" {
  description = "PostgreSQL service hostname"
  value       = upcloud_managed_database_postgresql.main.service_host
}

output "pg_port" {
  description = "PostgreSQL service port"
  value       = upcloud_managed_database_postgresql.main.service_port
}

# -----------------------------------------------------------------------------
# Valkey outputs
# -----------------------------------------------------------------------------
output "valkey_host" {
  description = "Valkey service hostname"
  value       = upcloud_managed_database_valkey.main.service_host
}

output "valkey_port" {
  description = "Valkey service port"
  value       = upcloud_managed_database_valkey.main.service_port
}

# -----------------------------------------------------------------------------
# Object Storage outputs
# -----------------------------------------------------------------------------
output "object_storage_endpoint" {
  description = "Managed Object Storage S3-compatible endpoint URL"
  value       = tolist(upcloud_managed_object_storage.main.endpoint)[0].domain_name
}

output "object_storage_username" {
  description = "Username of the app-service-account object storage user"
  value       = upcloud_managed_object_storage_user.app.username
}

# -----------------------------------------------------------------------------
# Kubernetes cluster outputs
# -----------------------------------------------------------------------------
output "cluster_id" {
  description = "UUID of the UKS Kubernetes cluster"
  value       = upcloud_kubernetes_cluster.main.id
}

output "cluster_name" {
  description = "Name of the UKS Kubernetes cluster"
  value       = upcloud_kubernetes_cluster.main.name
}

# -----------------------------------------------------------------------------
# Load Balancer outputs
# -----------------------------------------------------------------------------
output "lb_id" {
  description = "UUID of the Managed Load Balancer"
  value       = upcloud_loadbalancer.main.id
}

output "lb_dns_name" {
  description = "DNS name of the Managed Load Balancer (public operational address)"
  value       = [for n in upcloud_loadbalancer.main.networks : n.dns_name if n.type == "public"][0]
}
