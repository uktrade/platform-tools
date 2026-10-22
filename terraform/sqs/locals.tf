locals {

  # Build a map of all queue subscriptions as defined in platform-config.yml
  subscriptions = {
    for sub in var.config.subscribe_to :
    "${var.config.queue_name}:${sub.topic_name}" => {
      queue_name = var.config.queue_name
      topic_name = sub.topic_name
      topic_arn  = "arn:aws:sns:eu-west-2:${sub.account_id == null ? data.aws_caller_identity.current.account_id : sub.account_id}:${sub.topic_name}"
      raw_message_delivery = sub.raw_message_delivery
      filter_policy_scope  = sub.filter_policy_scope
      filter_policy        = sub.filter_policy
    }
  }
  # Todo add remote_subscriptions i.e. ones not created by the SNS module
}
