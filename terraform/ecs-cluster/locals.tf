locals {
  base_tags = {
    application = var.application
    environment = var.environment
    managed-by  = "DBT Platform - Environment Terraform"
  }

  schedule_tag = contains(["prod", "live"], lower(var.environment)) ? {} : { Schedule = "uk-office-hours" }

  tags = merge(local.base_tags, local.schedule_tag)

  cluster_name = "${var.application}-${var.environment}-cluster"
  sg_env_tags = merge(local.tags, {
    Name = "platform-${var.application}-${var.environment}-env-sg"
    }
  )
}
