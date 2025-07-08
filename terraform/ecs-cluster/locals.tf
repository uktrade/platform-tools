locals {
  tags = {
    application = var.application
    environment = var.environment
    managed-by  = "DBT Platform - Environment Terraform"
    Name        = "platform-${var.application}-${var.environment}-env-sg"
  }

  cluster_name = "${var.application}-${var.environment}-cluster"

}
