locals {
  tags = {
    application = var.application
    environment = var.environment
    managed-by  = "DBT Platform - Service Terraform"
  }

  service_name         = "${var.application}-${var.environment}-${var.service_config.name}"
  vpc_name             = var.env_config[var.environment]["vpc"]
  secrets              = values(coalesce(var.service_config.secrets, {}))
  web_service_required = var.service_config.type == "Load Balanced Web Service" ? 1 : 0
}
