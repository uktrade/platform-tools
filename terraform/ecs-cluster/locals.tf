locals {
  tags = {
    application = var.application
    environment = var.environment
    managed-by  = "DBT Platform - Environment Terraform"
  }

  cluster_name = "${var.application}-${var.environment}-cluster"

}
