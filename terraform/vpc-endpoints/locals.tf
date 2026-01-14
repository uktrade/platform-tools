locals {
  tags = {
    application = var.application
    environment = var.environment
    managed-by  = "DBT Platform - Environment Terraform"
  }

  sg_tags = merge(local.tags, {
    Name = "platform-${var.application}-${var.environment}-vpce-sg"
  })
}
