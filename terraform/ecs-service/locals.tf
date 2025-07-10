locals {
  tags = {
    application = var.application
    environment = var.environment
    managed-by  = "DBT Platform - Service Terraform"
  }

  service_name = var.service_config.name

  # TODO
  environment_overrides = lookup(var.service_config.environments, var.environment, {})
  merged_variables      = merge(var.service_config["variables"], lookup(local.environment_overrides, "variables", {}))
  merged_config         = merge(var.service_config, local.environment_overrides)

}