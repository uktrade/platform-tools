data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

resource "aws_sns_topic" "this" {
  name              = local.name
  kms_master_key_id = "alias/aws/sns"

  tags = local.tags
}

resource "aws_ssm_parameter" "sns_topic_arn" {
  # checkov:skip=CKV2_AWS_34: AWS SSM Parameter doesn't need to be Encrypted
  # checkov:skip=CKV_AWS_337: AWS SSM Parameter doesn't need to be Encrypted
  name  = "/platform/applications/${var.application}/environments/${var.environment}/extensions/sns/${local.name}-arn"
  type  = "String"
  value = aws_sns_topic.this.arn

  tags = local.tags
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
    sid    = "AllowSqsQueuesToSubscribeFromAllowedAccountSameOU"
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

    # Restricts subscribers to only use SQS queues
    condition {
      test     = "StringEquals"
      variable = "sns:Protocol"
      values   = ["sqs"]
    }

    # Condition 1: Must be from your specific allowed accounts list
    condition {
      test     = "StringEquals"
      variable = "aws:PrincipalAccount"
      values   = local.allowed_account_ids
    }

    # Condition 2: Must sit within the correct Organizational Unit hierarchy
    condition {
      test     = "ForAnyValue:StringLike"
      variable = "aws:PrincipalOrgPaths"
      values   = contains(["prod", "hotfix"], var.environment) ? local.org_ids.prod : local.org_ids.non_prod
    }
  }
}

resource "aws_sns_topic_policy" "this" {
  arn    = aws_sns_topic.this.arn
  policy = data.aws_iam_policy_document.sns_topic_policy.json
}
