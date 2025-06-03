data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "aws_iam_role" "codebase_pipeline_deploy" {
  name               = "${var.args.application}-${var.environment}-codebase-pipeline-deploy"
  assume_role_policy = data.aws_iam_policy_document.assume_codebase_pipeline.json
  tags               = local.tags
}

data "aws_iam_policy_document" "assume_codebase_pipeline" {
  statement {
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${local.pipeline_account_id}:root"]
    }
    condition {
      test = "ArnLike"
      values = [
        "arn:aws:iam::${local.pipeline_account_id}:role/${var.args.application}-*-codebase-pipeline",
        "arn:aws:iam::${local.pipeline_account_id}:role/${var.args.application}-*-codebase-pipeline-*",
        "arn:aws:iam::${local.pipeline_account_id}:role/${var.args.application}-*-codebase-*"
      ]
      variable = "aws:PrincipalArn"
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role_policy" "ecr_access" {
  name   = "ecr-access"
  role   = aws_iam_role.codebase_pipeline_deploy.name
  policy = data.aws_iam_policy_document.ecr_access.json
}

data "aws_iam_policy_document" "ecr_access" {
  statement {
    effect = "Allow"
    actions = [
      "ecr:DescribeImages"
    ]
    resources = [
      "arn:aws:ecr:${data.aws_region.current.name}:${local.pipeline_account_id}:repository/${var.args.application}/*"
    ]
  }
}

resource "aws_iam_role_policy" "artifact_store_access" {
  name   = "artifact-store-access"
  role   = aws_iam_role.codebase_pipeline_deploy.name
  policy = data.aws_iam_policy_document.artifact_store_access.json
}

data "aws_iam_policy_document" "artifact_store_access" {
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
      "arn:aws:s3:::${var.args.application}-*-cb-arts/*",
      "arn:aws:s3:::${var.args.application}-*-cb-arts"
    ]
  }

  statement {
    effect = "Allow"

    actions = [
      "codebuild:BatchGetBuilds",
      "codebuild:StartBuild",
      "codebuild:StopBuild"
    ]

    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "kms:GenerateDataKey",
      "kms:Decrypt"
    ]
    resources = [
      "arn:aws:kms:${data.aws_region.current.name}:${local.pipeline_account_id}:key/*"
    ]
  }
}

resource "aws_iam_role_policy" "ecs_deploy_access" {
  name   = "ecs-deploy-access"
  role   = aws_iam_role.codebase_pipeline_deploy.name
  policy = data.aws_iam_policy_document.ecs_deploy_access.json
}

data "aws_iam_policy_document" "ecs_deploy_access" {
  statement {
    effect = "Allow"
    actions = [
      "ecs:UpdateService",
      "ecs:DescribeServices",
      "ecs:TagResource",
      "ecs:ListServices"
    ]
    resources = [
      "arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:cluster/${var.args.application}-${var.environment}",
      "arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:service/${var.args.application}-${var.environment}/*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "ecs:DescribeTasks",
      "ecs:TagResource"
    ]
    resources = [
      "arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:cluster/${var.args.application}-${var.environment}",
      "arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:task/${var.args.application}-${var.environment}/*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "ecs:RunTask",
      "ecs:TagResource"
    ]
    resources = [
      "arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:task-definition/${var.args.application}-${var.environment}-*:*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "ecs:ListTasks"
    ]
    resources = [
      "arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:container-instance/${var.args.application}-${var.environment}/*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "ecs:RegisterTaskDefinition",
      "ecs:DescribeTaskDefinition"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "iam:PassRole"
    ]
    resources = ["*"]
    condition {
      test     = "StringLike"
      values   = ["ecs-tasks.amazonaws.com"]
      variable = "iam:PassedToService"
    }
  }

  statement {
    effect = "Allow"
    actions = [
      "ecs:ListServiceDeployments"
    ]
    resources = [
      "arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:service/${var.args.application}-${var.environment}/*"
    ]
  }
}

resource "aws_iam_role_policy" "cloudformation_access" {
  name   = "cloudformation-access"
  role   = aws_iam_role.codebase_pipeline_deploy.name
  policy = data.aws_iam_policy_document.cloudformation_access.json
}

data "aws_iam_policy_document" "cloudformation_access" {
  statement {
    effect = "Allow"
    actions = [
      "cloudformation:GetTemplate"
    ]
    resources = [
      "arn:aws:cloudformation:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:stack/${var.args.application}-${var.environment}-*"
    ]
  }
}

