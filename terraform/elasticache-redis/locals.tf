locals {
  redis_engine_version_map = {
    "7.2" = "valkey7"
    "7.1" = "redis7"
    "7.0" = "redis7"
    "6.2" = "redis6.x"
  }

  tags = {
    application         = var.application
    environment         = var.environment
    managed-by          = "DBT Platform - Terraform"
    copilot-application = var.application
    copilot-environment = var.environment
  }

  # Don't switch to Valkey for great prod account
  switch_to_valkey = !(var.application == "great" && (var.environment == "hotfix" || var.environment == "prod"))
  engine           = var.config.engine == "7.1" && local.switch_to_valkey ? "valkey" : "redis"
  engine_version   = var.config.engine == "7.1" && local.switch_to_valkey ? "7.2" : var.config.engine

  central_log_group_arns        = jsondecode(data.aws_ssm_parameter.log-destination-arn.value)
  central_log_group_destination = var.environment == "prod" ? local.central_log_group_arns["prod"] : local.central_log_group_arns["dev"]
}
