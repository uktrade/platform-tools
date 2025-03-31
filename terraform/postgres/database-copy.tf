module "database-dump" {
  count  = length(local.data_dump_tasks) > 0 ? 1 : 0
  source = "./database-dump"

  application   = var.application
  environment   = var.environment
  database_name = var.name
  tasks         = local.data_dump_tasks
}

module "database-load" {
  count  = length(local.data_load_tasks)
  source = "./database-load"

  application   = var.application
  environment   = var.environment
  database_name = var.name
  task          = local.data_load_tasks[count.index]
}

module "database-copy-pipeline" {
  count  = length(local.pipeline_tasks)
  source = "./database-copy-pipeline"

  application   = var.application
  environment   = var.environment
  database_name = var.name
  task          = local.pipeline_tasks[count.index]
}

resource "aws_ssm_parameter" "environment_config" {
  # checkov:skip=CKV_AWS_337: Used by copilot doesn't need to be encrypted
  # checkov:skip=CKV2_AWS_34: Used by copilot doesn't need to be encrypted
  for_each    = local.prod_account_environments
  name        = "/copilot/applications/${var.application}/environments/${each.key}"
  description = "Configuration for the ${each.key} environment, used by platform-helper commands"
  type        = "String"
  value = jsonencode({
    "app" : var.application,
    "name" : each.key,
    "region" : "eu-west-2",
    "accountID" : each.value
  })

  tags = local.tags
}
