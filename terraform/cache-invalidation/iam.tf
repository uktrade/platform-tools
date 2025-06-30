data "aws_region" "current" {}


data "aws_iam_policy_document" "dns_account_assume_role" {
  statement {
    sid    = "AllowDNSAccountAccess"
    effect = "Allow"
    actions = [
      "sts:AssumeRole",
    ]
    resources = [local.dns_account_assumed_role]
  }
}


resource "aws_iam_role_policy" "dns_account_assume_role_for_cache_invalidation" {
  name   = "${var.application}-${var.environment}-dns-account-assume-role"
  role   = aws_iam_role.cache_invalidation.name
  policy = data.aws_iam_policy_document.dns_account_assume_role.json
}


data "aws_iam_policy_document" "assume_codebuild_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${var.deploy_account_id}:role/${var.application}-${var.environment}-codebase-deploy"]
    }

    actions = ["sts:AssumeRole"]

  }
}

resource "aws_iam_role" "cache_invalidation" {
  name               = "${var.application}-${var.environment}-cache-invalidation"
  assume_role_policy = data.aws_iam_policy_document.assume_codebuild_role.json
  tags               = local.tags
}
