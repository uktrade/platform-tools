locals {

  secrets      = values(coalesce(var.service_config.secrets, {}))
  service_name = "${var.application}-${var.environment}-${var.service_config.name}"
  tags = {
    application = var.application
    environment = var.environment
    service     = var.service_config.name
    managed-by  = "DBT Platform - Service Terraform"
  }

  vpc_name             = var.env_config[var.environment]["vpc"]
  web_service_required = var.service_config.type == "Load Balanced Web Service" ? 1 : 0
}
