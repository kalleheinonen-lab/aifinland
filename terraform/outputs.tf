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
