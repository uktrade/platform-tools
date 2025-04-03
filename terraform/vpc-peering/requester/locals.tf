locals {
  tags = {
    managed-by     = "DBT Platform - Terraform"
    Name           = var.name
    remote-vpc     = var.config.accepter_vpc_name
    remote-account = var.config.accepter_account_id
  }
}
