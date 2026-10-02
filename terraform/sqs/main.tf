resource "aws_sqs_queue" "this" {
  for_each = local.queues

  name = each.value.queue_name
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
      aws_sqs_queue.this[each.value.queue_name].arn
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
  for_each = local.subscriptions
  queue_url = aws_sqs_queue.this[each.value.queue_name].id

  policy = data.aws_iam_policy_document.allow_sns_to_sqs[
    each.key
  ].json
}

## We're not doing cross-environment, but keep for possible use on cross-account
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
  endpoint = aws_sqs_queue.this[each.value.queue_name].arn
}