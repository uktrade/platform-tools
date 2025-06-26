locals {
  tags = {
    application         = var.application
    copilot-application = var.application
    managed-by          = "DBT Platform - Terraform"
  }

  dns_account_assumed_role = "arn:aws:iam::${var.dns_account_id}:role/environment-pipeline-assumed-role"
}
