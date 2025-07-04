locals {
  tags = {
    application = var.application
    environment = var.environment
    managed-by  = "DBT Platform - Terraform"
  }

  cluster_name = "${var.application}-${var.environment}-cluster"

  is_production_env   = contains(["prod", "production", "PROD", "PRODUCTION"], var.environment)
  log_destination_arn = local.is_production_env ? "arn:aws:logs:eu-west-2:812359060647:destination:cwl_log_destination" : "arn:aws:logs:eu-west-2:812359060647:destination:platform-logging-logstash-distributor-non-production"

}