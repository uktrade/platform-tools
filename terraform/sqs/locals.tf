locals {

  # Build a map of all queue subscriptions as defined in platform-config.yml
  subscriptions = {
    for sub in var.config.subscribe_to :
    "${var.config.queue_name}:${sub.topic_name}" => {
      queue_name       = var.config.queue_name
      topic_name       = sub.topic_name
      is_cross_account = sub.account_id != null
      topic_arn        = "arn:aws:sqs:eu-west-2:${sub.account_id}:${sub.topic_name}"
    }
  }
  # Todo add remote_subscriptions i.e. ones not created by the SNS module
}
