resource "random_string" "suffix" {
  length  = 8
  special = false
}

locals {
  tags = {
    application         = var.application
    environment         = var.environment
    managed-by          = "DBT Platform - Terraform"
    copilot-application = var.application
    copilot-environment = var.environment
  }

  name = "${var.application}-${var.environment}-${var.name}"

  version = var.config.version
  family  = local.version != null ? format("postgres%d", floor(local.version)) : null

  multi_az = coalesce(var.config.multi_az, false)

  skip_final_snapshot       = coalesce(var.config.skip_final_snapshot, false)
  final_snapshot_identifier = !local.skip_final_snapshot ? "${local.name}-${random_string.suffix.result}" : null
  snapshot_id               = var.config.snapshot_id
  volume_size               = coalesce(var.config.volume_size, 100)
  deletion_protection       = coalesce(var.config.deletion_protection, true)
  backup_retention_days     = coalesce(var.config.backup_retention_days, 7)

  instance_class = coalesce(var.config.instance, "db.t3.micro")
  storage_type   = coalesce(var.config.storage_type, "gp3")
  iops           = var.config.iops != null && local.storage_type != "gp3" ? var.config.iops : null

  secret_prefix                = upper(replace(var.name, "-", "_"))
  rds_master_secret_name       = "${local.secret_prefix}_RDS_MASTER_ARN"
  read_only_secret_name        = "${local.secret_prefix}_READ_ONLY_USER"
  application_user_secret_name = "${local.secret_prefix}_APPLICATION_USER"

  central_log_group_arns        = jsondecode(data.aws_ssm_parameter.log-destination-arn.value)
  central_log_group_destination = var.environment == "prod" ? local.central_log_group_arns["prod"] : local.central_log_group_arns["dev"]

  data_copy_tasks = coalesce(var.config.database_copy, [])

  base_env_config = {
    for name, config in var.env_config : name =>
    lookup(lookup(lookup(merge(lookup(var.env_config, "*", {}), config), "accounts", {}), "deploy", {}), "id", {}) if name != "*"
  }

  base_account_id = lookup(var.env_config, "*", {}).accounts.deploy.id

  data_dump_tasks = [for task in local.data_copy_tasks :
    merge(task, {
      from_account : lookup(local.base_env_config, task.from, null),
      to_account : lookup(local.base_env_config, task.to, null)
  }) if task.from == var.environment && !strcontains(task.to, "prod")]

  data_load_tasks = [for task in local.data_copy_tasks :
    merge(task, {
      from_account : lookup(local.base_env_config, task.from, null),
      to_account : lookup(local.base_env_config, task.to, null)
  }) if task.to == var.environment && !strcontains(task.to, "prod")]

  pipeline_tasks = [for task in local.data_load_tasks :
  task if lookup(task, "pipeline", null) != null]

  // Distinct list of environments with a dump or load operation in the prod AWS account
  prod_account_environments = { for env in toset(concat(
    [for task in local.data_dump_tasks : task.from if task.from_account != local.base_account_id],
    [for task in local.data_load_tasks : task.to if task.to_account != local.base_account_id]
  )) : env => lookup(local.base_env_config, env, null) }
}
