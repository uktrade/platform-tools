locals {
  tags = {
    application         = var.application
    environment         = var.environment
    managed-by          = "DBT Platform - Terraform"
    copilot-application = var.application
    copilot-environment = var.environment
  }

  task_name          = "${var.application}-${var.environment}-${var.database_name}-dump"
  dump_kms_key_alias = "alias/${local.task_name}"
  dump_bucket_name   = local.task_name

  pipeline_tasks = [for task in var.tasks : task if lookup(task, "pipeline", null) != null]
  region_account = "${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}"

  ecr_repository_arn = "arn:aws:ecr-public::763451185160:repository/database-copy"
}
