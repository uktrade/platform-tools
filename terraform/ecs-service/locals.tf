locals {
  tags = {
    application = var.application
    environment = var.environment
    managed-by  = "DBT Platform - Service Terraform"
  }

  service_name = var.service_config.name
}
