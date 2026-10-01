locals {
  name     = "${var.environment}-${var.application}-sqs-queue" #${var.queue_name}"
  dlq_name = "${local.name}-dlq"

  sns_topic_arns = [
    for subscription in values(var.sns_topic_subscriptions) :
    subscription.topic_arn
  ]

  create_topic_policy = var.allowed_sqs_subscriber_organization_id != null
}