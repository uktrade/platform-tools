// The DataDog Provider requires an API and APP key which we'll get from AWS Parameter Store
data "aws_ssm_parameter" "datadog_api_key" {
  name = "DATADOG_API_KEY"
}
data "aws_ssm_parameter" "datadog_app_key" {
  name = "DATADOG_APP_KEY"
}

module "s3" {
  source = "../s3"

  for_each = local.s3

  providers = {
    aws.domain-cdn = aws.domain-cdn
  }

  application = var.args.application
  environment = var.environment
  name        = each.key
  vpc_name    = local.vpc_name

  config = each.value
}

module "postgres" {
  source = "../postgres"

  for_each = local.postgres

  application = var.args.application
  environment = var.environment
  name        = each.key
  vpc_name    = local.vpc_name
  env_config  = var.args.env_config

  config = each.value
}

module "elasticache-redis" {
  source = "../elasticache-redis"

  for_each = local.redis

  application = var.args.application
  environment = var.environment
  name        = each.key
  vpc_name    = local.vpc_name

  config = each.value
}

module "opensearch" {
  source = "../opensearch"

  for_each = local.opensearch

  application = var.args.application
  environment = var.environment
  name        = each.key
  vpc_name    = local.vpc_name

  config = each.value
}

module "alb" {
  source = "../application-load-balancer"

  for_each = local.alb
  providers = {
    aws.domain = aws.domain
  }
  application    = var.args.application
  environment    = var.environment
  vpc_name       = local.vpc_name
  dns_account_id = local.dns_account_id

  config = each.value
}

module "cdn" {
  source = "../cdn"

  for_each = local.cdn
  providers = {
    aws.domain-cdn = aws.domain-cdn
  }
  application = var.args.application
  environment = var.environment

  origin_verify_secret_id = one(values(module.alb)).origin_verify_secret_id

  config = each.value
}

module "monitoring" {
  source = "../monitoring"

  for_each = local.monitoring

  application = var.args.application
  environment = var.environment
  vpc_name    = local.vpc_name

  config = each.value
}

resource "aws_ssm_parameter" "addons" {
  # checkov:skip=CKV_AWS_337: Used by copilot needs further analysis to ensure doesn't create similar issue to DBTP-1128 - raised as DBTP-1217
  # checkov:skip=CKV2_AWS_34: Used by copilot needs further analysis to ensure doesn't create similar issue to DBTP-1128 - raised as DBTP-1217
  name  = "/copilot/applications/${var.args.application}/environments/${var.environment}/addons"
  tier  = "Intelligent-Tiering"
  type  = "String"
  value = jsonencode(local.extensions_for_environment)
  tags  = local.tags
}

module "datadog" {
  source = "../datadog"

  for_each = local.datadog
  providers = {
    datadog.ddog = datadog.ddog
  }

  application = var.args.application

  config = each.value
}
