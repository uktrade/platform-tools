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

resource "aws_iam_role_policy" "iam_access_for_codebase" {
  name   = "iam-permissions"
  role   = aws_iam_role.codebase_pipeline_deploy.name
  policy = data.aws_iam_policy_document.iam_access_for_codebase.json
}

data "aws_iam_policy_document" "iam_access_for_codebase" {
  statement {
    effect = "Allow"
    actions = [
      "iam:AttachRolePolicy",
      "iam:DetachRolePolicy",
      "iam:CreatePolicy",
      "iam:DeletePolicy",
      "iam:TagPolicy",
      "iam:CreateRole",
      "iam:DeleteRole",
      "iam:TagRole",
      "iam:PutRolePolicy",
      "iam:GetRole",
      "iam:GetPolicy",
      "iam:GetPolicyVersion",
      "iam:ListRolePolicies",
      "iam:GetRolePolicy",
      "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole",
      "iam:ListPolicyVersions",
      "iam:DeleteRolePolicy",
      "iam:UpdateAssumeRolePolicy"
    ]
    resources = [
      "arn:aws:iam::${local.pipeline_account_id}:role/${var.args.application}-${var.environment}-*-ecs-task-role",
      "arn:aws:iam::${local.pipeline_account_id}:role/${var.args.application}-${var.environment}-*-ecs-task-execution-role",
      "arn:aws:iam::${local.pipeline_account_id}:policy/${var.args.application}-${var.environment}-*-secrets-policy",
      "arn:aws:iam::${local.pipeline_account_id}:policy/${var.args.application}-${var.environment}-*-execute-command-policy",
      "arn:aws:iam::${local.pipeline_account_id}:policy/${var.args.application}-${var.environment}-*-service-logs-policy",
      "arn:aws:iam::${local.pipeline_account_id}:policy/${var.args.application}-${var.environment}-*-appconfig-policy",
      "arn:aws:iam::${local.pipeline_account_id}:policy/${var.args.application}-${var.environment}-*-s3-policy",
      "arn:aws:iam::${local.pipeline_account_id}:policy/${var.args.application}-${var.environment}-*-custom-iam-policy"
    ]
  }
}

resource "aws_iam_role_policy" "ecs_service_access_for_codebase" {
  name   = "ecs-permissions"
  role   = aws_iam_role.codebase_pipeline_deploy.name
  policy = data.aws_iam_policy_document.ecs_service_access_for_codebase.json
}

data "aws_iam_policy_document" "ecs_service_access_for_codebase" {
  # checkov:skip=CKV_AWS_111:Permissions required for KMS key and target group creation
  # checkov:skip=CKV_AWS_356:Permissions required for KMS key and target group creation
  statement {
    effect = "Allow"
    actions = [
      "ecs:RegisterTaskDefinition"
    ]
    resources = [
      "arn:aws:ecs:${data.aws_region.current.region}:${local.pipeline_account_id}:task-definition/*",
      "arn:aws:ecs:${data.aws_region.current.region}:${local.pipeline_account_id}:task-definition/"
    ]
  }

  statement {
    sid = "AllowDeregister"
    actions = [
      "ecs:DeregisterTaskDefinition"
    ]
    resources = [
      "*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "ec2:DescribeVpcs",
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "ec2:DescribeVpcAttribute"
    ]
    resources = [
      "arn:aws:ec2:${data.aws_region.current.region}:${local.pipeline_account_id}:vpc/*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "servicediscovery:ListNamespaces",
      "servicediscovery:GetNamespace",
      "servicediscovery:ListTagsForResource",
      "servicediscovery:ListSevices",
      "servicediscovery:GetService",
      "servicediscovery:CreateService",
      "servicediscovery:UpdateService",
      "servicediscovery:DeleteService",
      "servicediscovery:TagResource"
    ]
    resources = [
      "arn:aws:servicediscovery:${data.aws_region.current.region}:${local.pipeline_account_id}:*"
    ]
  }

  statement {
    actions = [
      "kms:DeleteAlias",
      "kms:CreateAlias",
      "kms:TagResource",
      "kms:PutKeyPolicy",
      "kms:ScheduleKeyDeletion",
      "kms:EnableKeyRotation",
      "kms:UpdateAlias",
      "kms:DescribeKey",
      "kms:GetKeyPolicy",
      "kms:GetKeyRotationStatus",
      "kms:ListResourceTags"
    ]
    resources = [
      "arn:aws:kms:${data.aws_region.current.region}:${local.pipeline_account_id}:key/*"
    ]
  }

  statement {
    actions = [
      "kms:CreateAlias",
      "kms:DeleteAlias",
    ]
    resources = [
      "arn:aws:kms:${data.aws_region.current.region}:${local.pipeline_account_id}:alias/${var.args.application}-${var.environment}-*-ecs-service-logs-key"
    ]
  }

  statement {
    actions = [
      "kms:ListAliases",
      "kms:CreateKey",
    ]
    resources = [
      "*"
    ]
  }

  statement {
    actions = [
      "elasticloadbalancing:CreateTargetGroup",
      "elasticloadbalancing:DeleteTargetGroup",
      "elasticloadbalancing:ModifyTargetGroup",
      "elasticloadbalancing:ModifyTargetGroupAttributes",
      "elasticloadbalancing:AddTags",
      "elasticloadbalancing:RemoveTags",
      "elasticloadbalancing:DescribeTargetGroups",
      "elasticloadbalancing:DescribeTargetGroupAttributes",
      "elasticloadbalancing:DescribeTags",
      "elasticloadbalancing:DescribeLoadBalancers",
      "elasticloadbalancing:DescribeLoadBalancerAttributes",
      "elasticloadbalancing:DescribeListeners",
      "elasticloadbalancing:DescribeRules",
      "elasticloadbalancing:CreateRule",
      "elasticloadbalancing:DeleteRule"
    ]
    resources = [
      "*"
    ]
  }

  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:DeleteLogGroup",
      "logs:PutRetentionPolicy",
      "logs:TagResource",
      "logs:DescribeLogGroups",
      "logs:ListTagsForResource",
      "logs:ListTagsLogGroup",
      "logs:AssociateKmsKey",
      "logs:DescribeLogStreams"
    ]
    resources = [
      "arn:aws:logs:${data.aws_region.current.region}:${local.pipeline_account_id}:log-group:/platform/*"
    ]
  }

  statement {
    actions = [
      "logs:DescribeLogGroups",
      "logs:DescribeSubscriptionFilters",
      "logs:PutSubscriptionFilter"
    ]
    resources = [
      "arn:aws:logs:${data.aws_region.current.region}:${local.pipeline_account_id}:log-group::log-stream:",
      "arn:aws:logs:${data.aws_region.current.region}:${local.pipeline_account_id}:log-group:/platform/ecs/service/${var.args.application}/${var.environment}/*:log-stream:",
      local.central_log_group_destination
    ]
  }

  statement {
    actions = [
      "ecs:DescribeClusters"
    ]
    resources = [
      "arn:aws:logs:${data.aws_region.current.region}:${local.pipeline_account_id}:log-group::log-stream:",
      "arn:aws:ecs:${data.aws_region.current.region}:${local.pipeline_account_id}:cluster/${var.args.application}-${var.environment}-cluster"
    ]
  }

  statement {
    actions = [
      "ec2:DescribeSecurityGroups",
      "ec2:DescribeSubnets"
    ]
    resources = [
      "*"
    ]
  }

  statement {
    actions = [
      "s3:ListBucketVersions"
    ]
    resources = [
      "arn:aws:s3:::ecs-task-definitions-${var.args.application}-${var.environment}"
    ]
  }

  statement {
    actions = [
      "s3:GetObjectTagging",
      "s3:PutObjectTagging"
    ]
    resources = [
      "arn:aws:s3:::ecs-task-definitions-${var.args.application}-${var.environment}/${var.args.application}/${var.environment}/*.json"
    ]
  }

  statement {
    actions = [
      "lambda:InvokeFunction"
    ]
    resources = [
      "arn:aws:lambda:${data.aws_region.current.region}:${local.pipeline_account_id}:function:${var.args.application}-${var.environment}-listener-rule-organiser:$LATEST"
    ]
  }

  statement {
    actions = [
      "ecs:CreateService"
    ]
    resources = [
      "arn:aws:ecs:${data.aws_region.current.region}:${local.pipeline_account_id}:service/${var.args.application}-${var.environment}-cluster/*"
    ]
  }

  statement {
    actions = [
      "application-autoscaling:RegisterScalableTarget",
      "application-autoscaling:DescribeScalableTargets",
      "application-autoscaling:ListTagsForResource",
      "application-autoscaling:DeregisterScalableTarget",
      "application-autoscaling:PutScalingPolicy",
      "application-autoscaling:DescribeScalingPolicies",
      "application-autoscaling:DescribeScalingActivities",
      "application-autoscaling:DeleteScalingPolicy"
    ]
    resources = [
      "arn:aws:application-autoscaling:${data.aws_region.current.region}:${local.pipeline_account_id}:scalable-target/*"
    ]
  }
}

resource "aws_iam_role_policy" "validate_platform_config_for_codebase" {
  name   = "platform-config-validation-permissions-for-codebase-pipeline"
  role   = aws_iam_role.codebase_pipeline_deploy.name
  policy = data.aws_iam_policy_document.validate_platform_config_for_codebase.json
}

data "aws_iam_policy_document" "validate_platform_config_for_codebase" {
  statement {
    effect = "Allow"
    actions = [
      "elasticache:DescribeCacheEngineVersions",
      "es:ListVersions",
      "iam:ListAccountAliases"
    ]
    resources = ["*"]
  }

  statement {
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
      "ssm:GetParametersByPath"
    ]
    resources = [
      "arn:aws:ssm:${data.aws_region.current.region}:${local.pipeline_account_id}:parameter/copilot/${var.args.application}/*/secrets/*",
      "arn:aws:ssm:${data.aws_region.current.region}:${local.pipeline_account_id}:parameter/copilot/applications/${var.args.application}",
      "arn:aws:ssm:${data.aws_region.current.region}:${local.pipeline_account_id}:parameter/copilot/applications/${var.args.application}/*",
      "arn:aws:ssm:${data.aws_region.current.region}:${local.pipeline_account_id}:parameter/***"
    ]
  }

  statement {
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
    ]
    condition {
      test     = "StringEquals"
      variable = "ssm:ResourceTag/copilot-application"
      values   = ["__all__", var.args.application]
    }
    resources = [
      "arn:aws:ssm:${data.aws_region.current.region}:${local.pipeline_account_id}:parameter/***",
    ]
  }
}

resource "aws_iam_role_policy" "state_kms_key_access_for_codebase_codebuild" {
  name   = "${var.args.application}-state-kms-key-access-for-codebase-codebuild"
  role   = aws_iam_role.codebase_pipeline_deploy.name
  policy = data.aws_iam_policy_document.state_kms_key_access.json
}

data "aws_kms_key" "state_kms_key" {
  key_id = "alias/terraform-platform-state-s3-key-${local.deploy_account_name}"
}

data "aws_iam_policy_document" "state_kms_key_access" {
  statement {
    actions = [
      "kms:ListKeys",
      "kms:Decrypt",
      "kms:GenerateDataKey"
    ]
    resources = [
      data.aws_kms_key.state_kms_key.arn
    ]
  }
}

resource "aws_iam_role_policy" "state_bucket_access_for_codebase_codebuild" {
  name   = "${var.args.application}-state-bucket-access-for-codebase-codebuild"
  role   = aws_iam_role.codebase_pipeline_deploy.name
  policy = data.aws_iam_policy_document.state_bucket_access.json
}

data "aws_s3_bucket" "state_bucket" {
  bucket = "terraform-platform-state-${local.deploy_account_name}"
}

data "aws_iam_policy_document" "state_bucket_access" {
  statement {
    actions = [
      "s3:ListBucket",
      "s3:GetObject",
      "s3:PutObject"
    ]
    resources = [
      data.aws_s3_bucket.state_bucket.arn,
      "${data.aws_s3_bucket.state_bucket.arn}/*"
    ]
  }
}

resource "aws_iam_role_policy" "state_dynamo_db_access_for_environment_codebuild" {
  name   = "${var.args.application}-state-dynamo-db-access-for-environment-codebuild"
  role   = aws_iam_role.codebase_pipeline_deploy.name
  policy = data.aws_iam_policy_document.state_lock_dynamo_db_access.json
}

data "aws_iam_policy_document" "state_lock_dynamo_db_access" {
  statement {
    actions = [
      "dynamodb:DescribeTable",
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:DeleteItem"
    ]
    resources = [
      "arn:aws:dynamodb:${data.aws_region.current.region}:${local.pipeline_account_id}:table/terraform-platform-lockdb-${local.deploy_account_name}"
    ]
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
      "arn:aws:ecr:${data.aws_region.current.region}:${local.pipeline_account_id}:repository/${var.args.application}/*"
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
      "arn:aws:kms:${data.aws_region.current.region}:${local.pipeline_account_id}:key/*"
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
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:cluster/${var.args.application}-${var.environment}",
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:service/${var.args.application}-${var.environment}/*",
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:cluster/${var.args.application}-${var.environment}-cluster",
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:service/${var.args.application}-${var.environment}-cluster/*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "ecs:DescribeTasks",
      "ecs:TagResource"
    ]
    resources = [
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:cluster/${var.args.application}-${var.environment}",
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:task/${var.args.application}-${var.environment}/*",
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:cluster/${var.args.application}-${var.environment}-cluster",
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:task/${var.args.application}-${var.environment}-cluster/*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "ecs:RunTask",
      "ecs:TagResource"
    ]
    resources = [
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:task-definition/${var.args.application}-${var.environment}-*:*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "ecs:ListTasks"
    ]
    resources = [
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:container-instance/${var.args.application}-${var.environment}/*",
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:container-instance/${var.args.application}-${var.environment}-cluster/*"
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
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:service/${var.args.application}-${var.environment}/*"
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
      "arn:aws:cloudformation:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:stack/${var.args.application}-${var.environment}-*"
    ]
  }
}

