data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "aws_iam_role" "environment_pipeline_codepipeline" {
  name               = "${var.application}-${var.pipeline_name}-environment-pipeline-codepipeline"
  assume_role_policy = data.aws_iam_policy_document.assume_codepipeline_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "assume_codepipeline_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["codepipeline.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]

    condition {
      test     = "StringEquals"
      variable = "aws:SourceArn"
      values = [
        "arn:aws:codepipeline:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:${var.application}-${var.pipeline_name}-environment-pipeline"
      ]
    }
  }
}

resource "aws_iam_role_policy" "artifact_store_access_for_environment_pipeline" {
  name   = "artifact-store-access"
  role   = aws_iam_role.environment_pipeline_codepipeline.name
  policy = data.aws_iam_policy_document.access_artifact_store.json
}

data "aws_iam_policy_document" "access_artifact_store" {
  # checkov:skip=CKV_AWS_111:Permissions required to change ACLs on uploaded artifacts
  # checkov:skip=CKV_AWS_356:Permissions required to upload artifacts
  statement {
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:GetBucketVersioning",
      "s3:PutObjectAcl",
      "s3:PutObject",
    ]

    resources = [
      aws_s3_bucket.artifact_store.arn,
      "${aws_s3_bucket.artifact_store.arn}/*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "kms:GenerateDataKey",
      "kms:Decrypt"
    ]
    resources = [
      aws_kms_key.artifact_store_kms_key.arn
    ]
  }
}

resource "aws_iam_role_policy" "codestar_connection_access_for_environment_pipeline" {
  name   = "codestar-connection-access"
  role   = aws_iam_role.environment_pipeline_codepipeline.name
  policy = data.aws_iam_policy_document.codestar_connection_access.json
}

data "aws_iam_policy_document" "codestar_connection_access" {
  statement {
    effect = "Allow"
    actions = [
      "codestar-connections:UseConnection",
      "codestar-connections:ListConnections",
      "codestar-connections:ListTagsForResource",
      "codestar-connections:PassConnection"
    ]
    resources = [
      "arn:aws:codestar-connections:eu-west-2:${data.aws_caller_identity.current.account_id}:*"
    ]
  }
  statement {
    effect = "Allow"
    actions = [
      "codebuild:BatchGetBuilds",
      "codebuild:StartBuild",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role" "environment_pipeline_codebuild" {
  name               = "${var.application}-${var.pipeline_name}-environment-pipeline-codebuild"
  assume_role_policy = data.aws_iam_policy_document.assume_codebuild_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "assume_codebuild_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["codebuild.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]

    condition {
      test     = "StringEquals"
      variable = "aws:SourceArn"
      values = compact([
        "arn:aws:codebuild:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:project/${var.application}-${var.pipeline_name}-environment-pipeline-plan",
        "arn:aws:codebuild:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:project/${var.application}-${var.pipeline_name}-environment-pipeline-build",
        "arn:aws:codebuild:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:project/${var.application}-${var.pipeline_name}-environment-pipeline-apply"
      ])
    }
  }
}

resource "aws_iam_role_policy" "log_access_for_environment_codebuild" {
  name   = "log-access"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.log_access.json
}

data "aws_iam_policy_document" "log_access" {
  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:TagLogGroup"
    ]
    resources = [
      aws_cloudwatch_log_group.environment_pipeline_codebuild.arn,
      "${aws_cloudwatch_log_group.environment_pipeline_codebuild.arn}:*",
      "arn:aws:logs:${local.account_region}:log-group:*"
    ]
  }
}

resource "aws_iam_role_policy" "artifact_store_access_for_environment_codebuild" {
  name   = "artifact-store-access"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.access_artifact_store.json
}

resource "aws_iam_role_policy" "ssm_read_access_for_environment_codebuild" {
  name   = "ssm-access"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.ssm_access.json
}

data "aws_iam_policy_document" "ssm_access" {
  statement {
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters"
    ]
    resources = [
      "arn:aws:ssm:${local.account_region}:parameter/codebuild/slack_*"
    ]
  }
}
