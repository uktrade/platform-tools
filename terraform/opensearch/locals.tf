resource "random_string" "suffix" {
  length  = 8
  special = false
}

locals {
  tags = {
    application         = var.application
    environment         = var.environment
    managed-by          = "DBT Platform - Terraform"
    copilot-application = var.application
    copilot-environment = var.environment
  }

  name               = replace(var.name, "_", "-")
  domain_name        = substr(replace("${var.environment}-${local.name}", "_", "-"), 0, 28)
  ssm_parameter_name = "/copilot/${var.application}/${var.environment}/secrets/${upper(replace("${var.name}_ENDPOINT", "-", "_"))}"
  master_user        = "opensearch_user"
  urlencode_password = coalesce(var.config.urlencode_password, true)

  instances  = coalesce(var.config.instances, 1)
  zone_count = var.config.enable_ha ? local.instances : null
  subnets    = slice(sort(tolist(data.aws_subnets.private-subnets.ids)), 0, local.instances)

  auto_tune_desired_state       = startswith(var.config.instance, "t2") || startswith(var.config.instance, "t3") ? "DISABLED" : "ENABLED"
  auto_tune_rollback_on_disable = startswith(var.config.instance, "t2") || startswith(var.config.instance, "t3") ? "DEFAULT_ROLLBACK" : "NO_ROLLBACK"

  central_log_group_arns        = jsondecode(data.aws_ssm_parameter.log-destination-arn.value)
  central_log_group_destination = var.environment == "prod" ? local.central_log_group_arns["prod"] : local.central_log_group_arns["dev"]
}

resource "random_string" "lambda_suffix" {
  count = 2

  length    = 6
  min_lower = 6
  special   = false
  lower     = true
}

# Reuse rds-endpoint for sm
data "aws_security_group" "rds-endpoint" {
  name = "${var.vpc_name}-rds-endpoint-sg"
}

# Used by all lambdas
data "aws_iam_policy_document" "lambda-assume-role-policy" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}
