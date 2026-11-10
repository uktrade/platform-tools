locals {
  name = "${var.application}-${var.environment}-${var.name}"

  # Build a map of all queue subscriptions as defined in platform-config.yml
  subscriptions = {
    for sub in var.config.subscribe_to :
    "${var.name}:${coalesce(sub.application, var.application)}/${coalesce(sub.environment, var.environment)}/${sub.topic_name}" => {
      topic_name           = sub.topic_name
      application          = coalesce(sub.application, var.application)
      environment          = coalesce(sub.environment, var.environment)
      account_id           = coalesce(sub.account_id, data.aws_caller_identity.current.account_id)
      raw_message_delivery = var.config.raw_message_delivery
      filter_policy_scope  = var.config.filter_policy_scope
      filter_policy        = var.config.filter_policy
    }
  }

  tags = {
    application = var.application
    environment = var.environment
    managed-by  = "DBT Platform - Terraform"
  }
}
