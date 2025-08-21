locals {
  tags = {
    application         = var.application
    environment         = var.environment
    managed-by          = "DBT Platform - Terraform"
    copilot-application = var.application
    copilot-environment = var.environment
  }

  pipeline_name  = "${var.database_name}-${var.task.from}-to-${var.task.to}-copy-pipeline"
  region_account = "${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}"
  dump_role_arn  = "arn:aws:iam::${var.task.from_account}:role/${var.application}-${var.task.from}-${var.database_name}-dump-task"
  load_role_arn  = "arn:aws:iam::${var.task.to_account}:role/${var.application}-${var.task.to}-${var.database_name}-load-task"
}
