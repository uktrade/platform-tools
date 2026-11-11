data "aws_caller_identity" "current" {}

resource "aws_sqs_queue" "this" {
  name                       = local.name
  sqs_managed_sse_enabled    = true
  visibility_timeout_seconds = var.config.visibility_timeout_seconds
  delay_seconds              = var.config.delay_seconds
  max_message_size           = var.config.max_message_size
  message_retention_seconds  = var.config.message_retention_seconds
  receive_wait_time_seconds  = var.config.receive_wait_time_seconds

  redrive_policy = (
    var.config.dead_letter_queue.enabled
    ) ? jsonencode({
      deadLetterTargetArn = aws_sqs_queue.dlq[0].arn
      maxReceiveCount     = var.config.dead_letter_queue.max_receive_count
  }) : null

  tags = local.tags
}

resource "aws_ssm_parameter" "sqs_queue_arn" {
  # checkov:skip=CKV_AWS_337: AWS SSM Parameter doesn't need to be Encrypted
  name  = "/platform/${var.application}/${var.environment}/secrets/${upper(replace(var.name, "-", "_"))}_ARN"
  type  = "String"
  value = aws_sqs_queue.this.arn

  tags = local.tags
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
        for _, sub in local.subscriptions :
        "arn:aws:sns:eu-west-2:${sub.account_id}:${sub.application}-${sub.environment}-${sub.topic_name}"
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

  name                      = "${local.name}-dlq"
  sqs_managed_sse_enabled   = true
  message_retention_seconds = var.config.dead_letter_queue.message_retention_seconds

  tags = local.tags
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

  topic_arn            = "arn:aws:sns:eu-west-2:${each.value.account_id}:${each.value.application}-${each.value.environment}-${each.value.topic_name}"
  protocol             = "sqs"
  endpoint             = aws_sqs_queue.this.arn
  raw_message_delivery = each.value.raw_message_delivery
  filter_policy        = jsonencode(each.value.filter_policy)
  filter_policy_scope  = each.value.filter_policy_scope
}
