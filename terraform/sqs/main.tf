resource "aws_sqs_queue" "this" {
  name                       = var.config.queue_name
  sqs_managed_sse_enabled    = true
  visibility_timeout_seconds = var.config.visibility_timeout_seconds

  redrive_policy = (
    var.config.dead_letter_queue.enabled
    ) ? jsonencode({
      deadLetterTargetArn = aws_sqs_queue.dlq[0].arn
      maxReceiveCount     = var.config.dead_letter_queue.max_receive_count
  }) : null
}


data "aws_iam_policy_document" "allow_sns_to_sqs" {
  for_each = local.subscriptions

  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["sns.amazonaws.com"]
    }

    actions = [
      "sqs:SendMessage"
    ]

    resources = [
      aws_sqs_queue.this.arn
    ]

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"

      values = [
        (
          var.topics[each.value.topic_name].arn
        )
      ]
    }
  }
}

resource "aws_sqs_queue_policy" "this" {
  ## We're not doing cross-environment, but keep for use on cross-account
  # for_each = {
  #   for subscription in var.config.subscribe_to :
  #   subscription.topic_name => subscription
  # }
  for_each  = local.subscriptions
  queue_url = aws_sqs_queue.this.id

  policy = data.aws_iam_policy_document.allow_sns_to_sqs[
    each.key
  ].json
}

resource "aws_sqs_queue" "dlq" {
  count = var.config.dead_letter_queue.enabled ? 1 : 0

  name = "${var.config.queue_name}-dlq"
}

resource "aws_sqs_queue_redrive_allow_policy" "dlq" {
  count = var.config.dead_letter_queue.enabled ? 1 : 0

  queue_url = aws_sqs_queue.dlq[0].id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"

    sourceQueueArns = [
      aws_sqs_queue.this.arn
    ]
  })
}

## We're not doing cross-environment, but keep for use on cross-account
# only look up 'remote' topics, i.e. in another environment (or one day a different account?)
# data "aws_sns_topic" "remote" {
#   for_each = local.remote_subscriptions

#   name = "${var.application}-${each.value.source_environment}-${each.key}"
# }

# 
resource "aws_sns_topic_subscription" "this" {
  for_each = local.subscriptions

  topic_arn = var.topics[each.value.topic_name].arn
  ## We're not doing cross-environment, but keep for use on cross-account
  # topic_arn = (
  #   each.value.source_environment == var.environment
  #     ? var.topics[each.value.topic_name].arn
  #     : data.aws_sns_topic.remote[each.value.topic_name].arn
  # )

  protocol = "sqs"
  endpoint = aws_sqs_queue.this.arn
}
