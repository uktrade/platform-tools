resource "aws_sns_topic" "this" {
  name = "${var.environment}-${var.application}-${var.config.topic_name}"
}

resource "aws_sqs_queue" "this" {
  name = "${var.environment}-${var.application}-sqs-queue" #${var.queue_name}"
}

data "aws_iam_policy_document" "allow_sns" {
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
      values   = [aws_sns_topic.this.arn]
    }
  }
}

resource "aws_sqs_queue_policy" "this" {
  queue_url = aws_sqs_queue.this.id
  policy    = data.aws_iam_policy_document.allow_sns.json
}

resource "aws_sns_topic_subscription" "this" {
  topic_arn = aws_sns_topic.this.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.this.arn

  depends_on = [
    aws_sqs_queue_policy.this
  ]
}