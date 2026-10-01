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

  application    = var.args.application
  environment    = var.environment
  name           = each.key
  vpc_name       = local.vpc_name
  cdn_account_id = local.dns_account_id

  config = each.value
}

module "postgres" {
  source = "../postgres"

  for_each = local.postgres

  application       = var.args.application
  environment       = var.environment
  name              = each.key
  vpc_name          = local.vpc_name
  env_config        = var.args.env_config
  deploy_repository = var.deploy_repository

  config         = each.value
  pinned_version = var.pinned_version
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
    aws.domain     = aws.domain
    aws.domain-cdn = aws.domain-cdn
  }
  application             = var.args.application
  environment             = var.environment
  vpc_name                = local.vpc_name
  dns_account_id          = local.dns_account_id
  service_deployment_mode = local.service_deployment_mode

  name   = each.key
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

module "vpc_endpoints" {
  source = "../vpc-endpoints"

  count = local.vpc_endpoints != null ? 1 : 0

  application = var.args.application
  environment = var.environment
  vpc_name    = local.vpc_name

  endpoint_definitions = local.vpc_endpoints
}

module "ecs_cluster" {
  source = "../ecs-cluster"

  count = local.non_copilot_service_deployment_mode

  application                     = var.args.application
  environment                     = var.environment
  vpc_name                        = local.vpc_name
  alb_https_security_group_id     = try(one(values(module.alb)).https_security_group_id, null)
  has_vpc_endpoints               = local.vpc_endpoints != null
  vpc_endpoints_security_group_id = try(one(module.vpc_endpoints).security_group_id, null)
  egress_rules                    = local.egress_rules
}

module "datadog" {
  source = "../datadog"

  for_each = local.datadog
  providers = {
    datadog.ddog = datadog.ddog
  }

  application = var.args.application
  environment = var.environment
  repos       = var.repos
  config      = each.value
}

# module "sns-sqs" {
#   source = "../sns-sqs"
#   application = var.args.application
#   environment = var.environment
#   for_each    = local.sns-sqs
#   config      = each.value
#   #  topic_name  = "some-random-topic"
#   #queue_name = "queuey-mcqueueface"
#   #create_dlq = true
# }

#copy of seperate module testing
module "sns" {
  source = "../sns"

  for_each    = local.sns

  application = var.args.application
  environment = var.environment
  config      = each.value
}

# Add an SQS queue on it's own - what happens with the topic_arn bit if there's no SNS to sub to?
# repleace the replace below to use application name 

module "sqs" {
  source = "../sqs"

  for_each    = local.sqs

  application = var.args.application
  environment = var.environment
  config      = each.value
  topics = try(
    module.sns[
      replace(each.key, "-sqs", "-sns") #should replace this with application name
    ].topics,
    {}
  )
}

  #topic_arn   = module.sns[replace(each.key, "-sqs", "-sns")].topic_arn
  # topics = { #don't like this block - tidy it up somehow
  #   for topic_name in each.value.subscribe_to:
  #     topic_name => module.sns[
  #       replace(each.key, "-sqs", "-sns")
  #     ].topics[topic_name]
  # }

#   sns_topic_subscriptions = {
#     daveg_subscription = {
#       topic_arn = "arn:aws:sns:eu-west-2:563763463626:daveg-test-some-random-topic"
#     }
#   }

#   # Optional tuning
#   visibility_timeout_seconds = 60
#   create_dlq                 = true
#   max_receive_count          = 5

#   tags = {
#     Environment = "daveg"
#     Service     = "test"
#   }
# }

resource "aws_ssm_parameter" "addons" {
  # checkov:skip=CKV_AWS_337: Used by copilot needs further analysis to ensure doesn't create similar issue to DBTP-1128 - raised as DBTP-1217
  # checkov:skip=CKV2_AWS_34: Used by copilot needs further analysis to ensure doesn't create similar issue to DBTP-1128 - raised as DBTP-1217
  name  = "/copilot/applications/${var.args.application}/environments/${var.environment}/addons"
  tier  = "Intelligent-Tiering"
  type  = "String"
  value = jsonencode(local.extensions_for_environment)
  tags  = local.tags
}

resource "aws_ssm_parameter" "environment_data" {
  # checkov:skip=CKV2_AWS_34: This AWS SSM Parameter doesn't need to be encrypted
  name = "/platform/applications/${var.args.application}/environments/${var.environment}"
  tier = "Intelligent-Tiering"
  type = "String"
  value = jsonencode({
    "name" : var.environment,
    "app" : var.args.application,
    "accountID" : local.deploy_account_id
    "region" : "eu-west-2",
    "vpc_name" : local.vpc_name,
    "service_deployment_mode" : local.service_deployment_mode,
    allEnvironments = [
      for env_name, env_config in var.args.env_config : {
        name      = env_name
        accountID = env_config["accounts"]["deploy"]["id"]
        region    = "eu-west-2"
      } if env_name != "*"
    ]
  })
  tags = local.tags
}

data "aws_ssm_parameter" "log_destination_arn" {
  name = "/copilot/tools/central_log_groups"
}


