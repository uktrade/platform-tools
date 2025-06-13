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
        "arn:aws:codepipeline:${local.account_region}:${var.application}-${var.pipeline_name}-environment-pipeline"
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
  # checkov:skip=CKV_AWS_111:Permissions required to change ACLs on uploaded artifacts
  # checkov:skip=CKV_AWS_356:Permissions required to upload artifacts
  statement {
    effect = "Allow"
    actions = [
      "codestar-connections:UseConnection",
      "codestar-connections:ListConnections",
      "codestar-connections:ListTagsForResource",
      "codestar-connections:PassConnection"
    ]
    resources = [
      "arn:aws:codestar-connections:${local.account_region}:*"
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
      values = [
        "arn:aws:codebuild:${local.account_region}:project/${var.application}-${var.pipeline_name}-environment-pipeline-plan",
        "arn:aws:codebuild:${local.account_region}:project/${var.application}-${var.pipeline_name}-environment-pipeline-build",
        "arn:aws:codebuild:${local.account_region}:project/${var.application}-${var.pipeline_name}-environment-pipeline-apply"
      ]
    }
  }
}

resource "aws_iam_role_policy" "codestar_connection_access_for_environment_codebuild" {
  name   = "codestar-connection-access"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.codestar_connection_access.json
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
      "arn:aws:logs:${local.account_region}:log-group:codebuild/${var.application}-${var.pipeline_name}-environment-terraform/log-group",
      "arn:aws:logs:${local.account_region}:log-group:codebuild/${var.application}-${var.pipeline_name}-environment-terraform/log-group:*"
    ]
  }
}

resource "aws_iam_role_policy" "artifact_store_access_for_environment_codebuild" {
  name   = "artifact-store-access"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.access_artifact_store.json
}

resource "aws_iam_role_policy" "ssm_access_for_environment_codebuild" {
  name   = "ssm-access"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.ssm_access.json
}

data "aws_iam_policy_document" "ssm_access" {
  statement {
    effect = "Allow"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters"
    ]
    resources = [
      "arn:aws:ssm:${local.account_region}:parameter/codebuild/slack_*"
    ]
  }
}

resource "aws_iam_role_policy" "codepipeline_access_for_environment_codebuild" {
  name   = "codepipeline-access"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.codepipeline_access.json
}

data "aws_iam_policy_document" "codepipeline_access" {
  statement {
    effect = "Allow"
    actions = [
      "codepipeline:GetPipelineState",
      "codepipeline:GetPipelineExecution",
      "codepipeline:ListPipelineExecutions",
      "codepipeline:StopPipelineExecution",
      "codepipeline:UpdatePipeline"
    ]
    resources = [
      "arn:aws:codepipeline:${local.account_region}:${var.application}-${var.pipeline_name}-environment-pipeline"
    ]
  }
}

resource "aws_iam_role_policy" "environment_deploy_role_access_for_environment_codebuild" {
  name   = "environment-deploy-role-access"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.environment_deploy_role_access.json
}

data "aws_iam_policy_document" "environment_deploy_role_access" {
  statement {
    effect = "Allow"
    actions = [
      "sts:AssumeRole"
    ]
    resources = [
      for env in local.environment_config :
      "arn:aws:iam::${env.accounts.deploy.id}:role/${var.application}-${env.name}-environment-pipeline-deploy"
    ]
  }
}

resource "aws_iam_role_policy" "copilot_access_for_environment_codebuild" {
  name   = "copilot-access"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.copilot_access.json
}

data "aws_iam_policy_document" "copilot_access" {
  statement {
    effect = "Allow"
    actions = [
      "sts:AssumeRole"
    ]
    resources = [
      for env in local.environment_config :
      "arn:aws:iam::${env.accounts.deploy.id}:role/${var.application}-${env.name}-EnvManagerRole"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "ssm:PutParameter",
      "ssm:GetParameter",
      "ssm:GetParameters",
      "ssm:GetParametersByPath",
      "ssm:DeleteParameter",
      "ssm:AddTagsToResource",
      "ssm:ListTagsForResource"
    ]
    resources = [
      "arn:aws:ssm:${local.account_region}:parameter/copilot/${var.application}/*/secrets/*",
      "arn:aws:ssm:${local.account_region}:parameter/copilot/applications/${var.application}",
      "arn:aws:ssm:${local.account_region}:parameter/copilot/applications/${var.application}/*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "iam:PassRole"
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.application}-adminrole"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "kms:GenerateDataKey",
      "kms:Decrypt"
    ]
    resources = [
      "arn:aws:kms:${local.account_region}:key/*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "s3:*",
    ]
    resources = [
      "arn:aws:s3:::stackset-${var.application}-*-pipelinebuiltartifactbuc-*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "cloudformation:GetTemplate",
      "cloudformation:GetTemplateSummary",
      "cloudformation:DescribeStackSet",
      "cloudformation:UpdateStackSet",
      "cloudformation:DescribeStackSetOperation",
      "cloudformation:ListStackInstances",
      "cloudformation:DescribeStacks",
      "cloudformation:DescribeChangeSet",
      "cloudformation:CreateChangeSet",
      "cloudformation:ExecuteChangeSet",
      "cloudformation:DescribeStackEvents",
      "cloudformation:DeleteStack"
    ]
    resources = [
      "arn:aws:cloudformation:${local.account_region}:stack/${var.application}-*",
      "arn:aws:cloudformation:${local.account_region}:stack/StackSet-${var.application}-infrastructure-*",
      "arn:aws:cloudformation:${local.account_region}:stackset/${var.application}-infrastructure:*",
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "cloudformation:ListExports"
    ]
    resources = ["*"]
  }
}
