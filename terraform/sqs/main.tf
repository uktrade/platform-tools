# resource "aws_sqs_queue" "this" {
#   for_each = var.config.subscribe_to
#   name = "${var.environment}-${var.application}-subscribe-to-${each.value}" #${var.config.subscribe_to}"
# }

# refactor above, based on source env added as a new option in platform-config,
# therefore we now refer to a local to loop through looking for topics to subscribe to
# also use app-env not env-app,, which should prob be a local tbh
# resource "aws_sqs_queue" "sub_to_sns" {
#   for_each = local.subscriptions

#   name = "${var.config.queue_name}-subscribe-to-${each.key}"
#   #name = "${var.application}-${var.environment}-subscribe-to-${each.key}" #each.value.topic_name}"

# }

# resource "aws_sqs_queue" "this" {
#   for_each = toset(var.config.queue_name)

#   name = "${var.config.queue_name}-${each.value}"
# }

resource "aws_sqs_queue" "this" {
  for_each = local.queues

  name                       = each.value.queue_name
  visibility_timeout_seconds = each.value.visibility_timeout_seconds

  redrive_policy = (
    each.value.dead_letter_queue.enabled
    ) ? jsonencode({
      deadLetterTargetArn = aws_sqs_queue.dlq[each.key].arn
      maxReceiveCount     = each.value.dead_letter_queue.max_receive_count
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
  # for_each = {
  #   for subscription in var.config.subscribe_to :
  #   subscription.topic_name => subscription
  # }
  for_each  = local.subscriptions
  queue_url = aws_sqs_queue.this[each.value.queue_name].id

  policy = data.aws_iam_policy_document.allow_sns_to_sqs[
    each.key
  ].json
}

resource "aws_sqs_queue" "dlq" {
  for_each = {
    for k, v in local.queues : k => v
    if v.dead_letter_queue.enabled
  }

  name = "${each.key}-dlq"
}

resource "aws_sqs_queue_redrive_allow_policy" "dlq" {
  for_each = aws_sqs_queue.dlq

  queue_url = each.value.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"

    sourceQueueArns = [
      aws_sqs_queue.queue[each.key].arn
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
  # topic_arn = (
  #   each.value.source_environment == var.environment
  #     ? var.topics[each.value.topic_name].arn
  #     : data.aws_sns_topic.remote[each.value.topic_name].arn
  # )

  protocol = "sqs"
  endpoint = aws_sqs_queue.this[each.value.queue_name].arn
}



# resource "aws_sns_topic_subscription" "this" {
#   for_each = {
#     for subscription in var.config.subscribe_to :
#     subscription.topic_name => subscription
#   }

#   topic_arn = data.aws_sns_topic.this[each.key].arn
#   protocol  = "sqs"
#   endpoint  = aws_sqs_queue.this[each.key].arn
# }

# resource "aws_sns_topic_subscription" "this" {
#   for_each = toset(var.config.subscribe_to)

#   topic_arn = var.topics[each.value].arn
#   protocol  = "sqs"
#   endpoint  = aws_sqs_queue.this[each.key].arn
# }

# resource "aws_sns_topic_subscription" "this" {
#   for_each = var.topics

#   topic_arn = each.value.arn
#   protocol  = "sqs"
#   endpoint  = aws_sqs_queue.this.arn
# }

# resource "aws_sns_topic_subscription" "this" {
#   topic_arn = var.topic_arn #data.aws_sns_topic.example.arn
#   protocol  = "sqs"
#   endpoint  = aws_sqs_queue.this.arn

#   depends_on = [
#     aws_sqs_queue_policy.this
#   ]
# }