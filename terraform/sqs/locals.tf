locals {

  # Build a map of all queue subscriptions as defined in platform-config.yml
  subscriptions = {
    for sub in var.config.subscribe_to :
    "${var.config.queue_name}:${sub.topic_name}" => {
      queue_name = var.config.queue_name
      topic_name = sub.topic_name
    }
  }

  # Todo addd remote_subscriptions i.e. ones not created by the SNS module

}
