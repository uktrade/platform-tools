locals {
  tags = {
    managed-by     = "DBT Platform - Terraform"
    Name           = var.name
    remote-vpc     = var.config.producer_vpc_name
    remote-account = var.config.producer_account_id
    application    = var.config.producer_application
    environment    = var.config.producer_environment
  }
}
