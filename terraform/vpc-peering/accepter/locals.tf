locals {
  tags = {
    Name       = var.name
    managed-by = "DBT Platform - Terraform"
    remote-vpc = var.config.requester_vpc_name
  }
}
