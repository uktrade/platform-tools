locals {
  tags = {
    application = var.application
    environment = var.environment
    managed-by  = "DBT Platform - Environment Terraform"
  }

  cluster_name = "${var.application}-${var.environment}-cluster"
  sg_env_tags = merge(local.tags, {
    Name = "platform-${var.application}-${var.environment}-env-sg"
    }
  )
}
