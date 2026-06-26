locals {
  tags = {
    managed-by     = "DBT Platform - Terraform"
    Name           = var.name
    remote-vpc     = var.config.consumer_vpc_name
    remote-account = var.config.consumer_account_id
    application    = var.config.consumer_application
    environment    = var.config.consumer_environment
  }
}
