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
