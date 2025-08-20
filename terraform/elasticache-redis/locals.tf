locals {
  redis_engine_version_map = {
    "7.1" = "redis7"
    "7.0" = "redis7"
    "6.2" = "redis6.x"
  }

  base_tags = {
    application         = var.application
    environment         = var.environment
    managed-by          = "DBT Platform - Terraform"
    copilot-application = var.application
    copilot-environment = var.environment
  }

  schedule_tag = contains(["prod", "live"], lower(var.environment)) ? {} : { Schedule = "uk-office-hours" }

  tags = merge(local.base_tags, local.schedule_tag)

  central_log_group_arns        = jsondecode(data.aws_ssm_parameter.log-destination-arn.value)
  central_log_group_destination = var.environment == "prod" ? local.central_log_group_arns["prod"] : local.central_log_group_arns["dev"]
}
