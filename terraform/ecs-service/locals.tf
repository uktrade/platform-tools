locals {
  base_tags = {
    application = var.application
    environment = var.environment
    managed-by  = "DBT Platform - Service Terraform"
  }

  schedule_tag = contains(["prod", "live"], lower(var.environment)) ? {} : { Schedule = "uk-office-hours" }

  tags = merge(local.base_tags, local.schedule_tag)

  service_name         = "${var.application}-${var.environment}-${var.service_config.name}"
  vpc_name             = var.env_config[var.environment]["vpc"]
  secrets              = values(var.service_config.secrets)
  web_service_required = var.service_config.type == "Load Balanced Web Service" ? 1 : 0
}
