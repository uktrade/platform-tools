resource "aws_sns_topic" "this" {
  for_each = var.config.topic_name
  name = "${var.application}-${var.environment}-${each.value}"  #${var.config.topic_name}"
}

data "aws_iam_policy_document" "sns_topic_policy" {
  for_each = aws_sns_topic.this

  statement {
    sid    = "AllowSqsQueuesToSubscribeFromOrganization"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    actions = [
      "sns:Subscribe"
    ]

    resources = [
      each.value.arn
    ]

    condition {
      test     = "StringEquals"
      variable = "sns:Protocol"
      values   = ["sqs"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:PrincipalOrgID"
      values   = [var.allowed_sqs_subscriber_organization_id]
    }
  }
}

resource "aws_sns_topic_policy" "this" {
  for_each = aws_sns_topic.this

  arn    = each.value.arn
  policy = data.aws_iam_policy_document.sns_topic_policy[each.key].json
}