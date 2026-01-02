# Pass-through so that parent modules can test the value provided for this variable.
output "instances" {
  value = var.instances
}

output "security_group_id" {
  value = aws_security_group.main.id
}
