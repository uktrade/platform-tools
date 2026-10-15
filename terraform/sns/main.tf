resource "aws_sns_topic" "this" {
  name              = var.config.topic_name
  kms_master_key_id = "alias/aws/sns"
}

data "aws_iam_policy_document" "sns_topic_policy" {
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

  arn    = aws_sns_topic.this.arn
  policy = data.aws_iam_policy_document.sns_topic_policy.json
}