data "aws_caller_identity" "current" {}

resource "aws_sqs_queue" "this" {
  name                       = "${var.application}-${var.environment}-${var.config.queue_name}"
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
        for _, subscription in local.subscriptions :
        subscription.topic_arn
      ]
    }
  }
}

resource "aws_sqs_queue_policy" "this" {
  queue_url = aws_sqs_queue.this.id

  policy = data.aws_iam_policy_document.allow_sns_to_sqs.json
}

resource "aws_sqs_queue" "dlq" {
  count = var.config.dead_letter_queue.enabled ? 1 : 0

  name                    = "${var.application}-${var.environment}-${var.config.queue_name}-dlq"
  sqs_managed_sse_enabled = true
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

resource "aws_sns_topic_subscription" "this" {
  for_each = local.subscriptions

  topic_arn = each.value.topic_arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.this.arn
  raw_message_delivery = each.value.raw_message_delivery
  filter_policy        = jsonencode(each.value.filter_policy)
  filter_policy_scope  = each.value.filter_policy_scope
}
