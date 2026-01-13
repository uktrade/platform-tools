# Pass-through so that parent modules can test the value provided for this variable.
output "endpoint_definitions" {
  value = var.endpoint_definitions
}

output "security_group_id" {
  value = aws_security_group.main.id
}
