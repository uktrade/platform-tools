locals {
  tags = {
    application         = var.application
    environment         = var.environment
    managed-by          = "DBT Platform - Terraform"
    copilot-application = var.application
    copilot-environment = var.environment
  }

  task_name = "${var.application}-${var.environment}-${var.database_name}-load"

  dump_task_name   = "${var.application}-${var.task.from}-${var.database_name}-dump"
  dump_bucket_name = local.dump_task_name

  pipeline_task  = lookup(var.task, "pipeline", null) != null
  region_account = "${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}"

  ecr_repository_arn = "arn:aws:ecr-public::763451185160:repository/database-copy"
}
