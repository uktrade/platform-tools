data "aws_caller_identity" "current" {}

resource "aws_sns_topic" "this" {
  name              = var.config.topic_name
  kms_master_key_id = "alias/aws/sns"
}

data "aws_iam_policy_document" "sns_topic_policy" {
  statement {
    actions = [
      "SNS:Subscribe",
      "SNS:SetTopicAttributes",
      "SNS:RemovePermission",
      "SNS:Publish",
      "SNS:ListSubscriptionsByTopic",
      "SNS:GetTopicAttributes",
      "SNS:DeleteTopic",
      "SNS:AddPermission",
    ]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceOwner"

      values = [
        data.aws_caller_identity.current.account_id,
      ]
    }

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    resources = [
      aws_sns_topic.this.arn
    ]
  }

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
      aws_sns_topic.this.arn
    ]

    condition {
      test     = "StringEquals"
      variable = "sns:Protocol"
      values   = ["sqs"]
    }

    condition {
      test     = "StringLike"
      variable = "sns:Endpoint"
      values   = var.config.allow_list
    }
  }
}

resource "aws_sns_topic_policy" "this" {
  for_each = aws_sns_topic.this

  arn    = aws_sns_topic.this.arn
  policy = data.aws_iam_policy_document.sns_topic_policy.json
}