# Pass-through so that parent modules can test the value provided for this variable.
output "has_vpc_endpoints" {
  value = var.has_vpc_endpoints
}

# Pass-through so that parent modules can test the value provided for this variable.
output "egress_rules" {
  value = var.egress_rules
}
