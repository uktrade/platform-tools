data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

data "aws_organizations_organization" "org" {}

data "aws_organizations_organizational_units" "ou" {
  parent_id = data.aws_organizations_organization.org.roots[0].id
}

data "aws_organizations_entity_path" "entity" {
  entity_id = data.aws_organizations_organizational_units.ou.children[0].id
}

resource "aws_sns_topic" "this" {
  name              = "${var.application}-${var.environment}-${var.config.topic_name}"
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
      test     = "ForAnyValue:StringEquals"
      variable = "aws:PrincipalOrgPaths"
      values   = [data.aws_organizations_entity_path.entity.entity_path]
    }
  }
}

resource "aws_sns_topic_policy" "this" {
  arn    = aws_sns_topic.this.arn
  policy = data.aws_iam_policy_document.sns_topic_policy.json
}