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
        for k, v in local.subscriptions :
        v.is_cross_account ? v.topic_arn : var.topics[v.topic_name].arn
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

  name                    = "${var.config.queue_name}-dlq"
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

  topic_arn = each.value.is_cross_account ? each.value.topic_arn : var.topics[each.value.topic_name].arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.this.arn
}
