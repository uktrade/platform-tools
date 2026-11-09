locals {

  # Build a map of all queue subscriptions as defined in platform-config.yml
  subscriptions = {
    for sub in var.config.subscribe_to :
    "${var.config.queue_name}:${sub.topic_name}" => {
      queue_name           = var.config.queue_name
      topic_name           = sub.topic_name
      topic_arn            = "arn:aws:sns:eu-west-2:${sub.account_id == null ? data.aws_caller_identity.current.account_id : sub.account_id}:${sub.topic_name}"
      raw_message_delivery = var.config.raw_message_delivery
      filter_policy_scope  = var.config.filter_policy_scope
      filter_policy        = var.config.filter_policy
    }
  }

  tags = {
    application         = var.application
    environment         = var.environment
    managed-by          = "DBT Platform - Terraform"
    copilot-application = var.application
    copilot-environment = var.environment
  }
}
