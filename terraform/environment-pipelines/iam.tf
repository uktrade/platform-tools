data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

data "aws_iam_policy_document" "assume_codepipeline_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["codepipeline.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
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
    effect    = "Allow"
    actions   = ["codestar-connections:UseConnection"]
    resources = [data.aws_codestarconnections_connection.github_codestar_connection.arn]
  }

  statement {
    effect = "Allow"
    actions = [
      "codestar-connections:ListConnections",
      "codestar-connections:ListTagsForResource",
      "codestar-connections:PassConnection"
    ]
    resources = ["arn:aws:codestar-connections:eu-west-2:${data.aws_caller_identity.current.account_id}:*"]
  }

  statement {
    effect = "Allow"

    actions = [
      "codebuild:BatchGetBuilds",
      "codebuild:StartBuild",
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
      aws_kms_key.artifact_store_kms_key.arn
    ]
  }
}

data "aws_iam_policy_document" "assume_codebuild_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["codebuild.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }

  statement {
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }

    actions = ["sts:AssumeRole"]

    condition {
      test     = "StringLike"
      variable = "sts:RoleSessionName"

      values = [
        "environment-pipeline-platform-helper-generate-*"
      ]
    }
  }

  dynamic "statement" {
    for_each = toset(local.triggers_another_pipeline ? [""] : [])
    content {
      effect = "Allow"

      principals {
        type        = "AWS"
        identifiers = [local.triggered_pipeline_codebuild_role]
      }

      actions = ["sts:AssumeRole"]
    }
  }
}

data "aws_iam_policy_document" "write_environment_pipeline_codebuild_logs" {
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

data "aws_s3_bucket" "state_bucket" {
  bucket = "terraform-platform-state-${local.stages[0].accounts.deploy.name}"
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

data "aws_kms_key" "state_kms_key" {
  key_id = "alias/terraform-platform-state-s3-key-${local.stages[0].accounts.deploy.name}"
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

data "aws_iam_policy_document" "state_dynamo_db_access" {
  statement {
    actions = [
      "dynamodb:DescribeTable",
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:DeleteItem"
    ]
    resources = [
      "arn:aws:dynamodb:${local.account_region}:table/terraform-platform-lockdb-${local.stages[0].accounts.deploy.name}"
    ]
  }
}

data "aws_iam_policy_document" "ec2_read_access" {
  statement {
    actions = [
      "ec2:DescribeVpcs",
      "ec2:DescribeSubnets",
      "ec2:DescribeSecurityGroups",
      "ec2:DescribeNetworkInterfaces"
    ]
    resources = [
      "*"
    ]
  }

  statement {
    actions = [
      "ec2:DescribeVpcAttribute",
      "ec2:CreateSecurityGroup"
    ]
    resources = [
      "arn:aws:ec2:${local.account_region}:vpc/*"
    ]
  }
}

data "aws_ssm_parameter" "central_log_group_parameter" {
  name = "/copilot/tools/central_log_groups"
}

data "aws_iam_policy_document" "ssm_read_access" {
  statement {
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters"
    ]
    resources = [
      data.aws_ssm_parameter.central_log_group_parameter.arn,
      "arn:aws:ssm:${local.account_region}:parameter/codebuild/slack_*"
    ]
  }
}

data "aws_iam_policy_document" "dns_account_assume_role" {
  statement {
    actions = [
      "sts:AssumeRole"
    ]
    resources = local.dns_account_assumed_roles
  }
}

data "aws_iam_policy_document" "load_balancer" {
  statement {
    actions = [
      "elasticloadbalancing:DescribeTargetGroups",
      "elasticloadbalancing:DescribeTargetGroupAttributes",
      "elasticloadbalancing:DescribeTags",
      "elasticloadbalancing:DescribeLoadBalancers",
      "elasticloadbalancing:DescribeLoadBalancerAttributes",
      "elasticloadbalancing:DescribeSSLPolicies",
      "elasticloadbalancing:DescribeListeners",
      "elasticloadbalancing:DescribeTargetHealth",
      "elasticloadbalancing:DescribeRules",
      "elasticloadbalancing:DescribeListenerCertificates",
      "elasticloadbalancing:DescribeListenerAttributes"
    ]
    resources = [
      "*"
    ]
  }

  dynamic "statement" {
    for_each = local.environment_config
    content {
      actions = [
        "elasticloadbalancing:CreateTargetGroup",
        "elasticloadbalancing:AddTags",
        "elasticloadbalancing:ModifyTargetGroupAttributes",
        "elasticloadbalancing:DeleteTargetGroup"
      ]
      resources = [
        "arn:aws:elasticloadbalancing:${local.account_region}:targetgroup/${var.application}-${statement.value.name}-http/*"
      ]
    }
  }

  dynamic "statement" {
    for_each = local.environment_config
    content {
      actions = [
        "elasticloadbalancing:CreateLoadBalancer",
        "elasticloadbalancing:AddTags",
        "elasticloadbalancing:ModifyLoadBalancerAttributes",
        "elasticloadbalancing:DeleteLoadBalancer",
        "elasticloadbalancing:CreateListener",
        "elasticloadbalancing:ModifyListener",
        "elasticloadbalancing:SetWebACL"
      ]
      resources = [
        "arn:aws:elasticloadbalancing:${local.account_region}:loadbalancer/app/${var.application}-${statement.value.name}/*"
      ]
    }
  }

  dynamic "statement" {
    for_each = local.environment_config
    content {
      actions = [
        "elasticloadbalancing:AddTags",
        "elasticloadbalancing:ModifyListener"
      ]
      resources = [
        "arn:aws:elasticloadbalancing:${local.account_region}:listener/app/${var.application}-${statement.value.name}/*"
      ]
    }
  }

  statement {
    actions = [
      "cloudfront:ListCachePolicies",
      "cloudfront:GetCachePolicy"
    ]
    resources = [
      "arn:aws:cloudfront::${data.aws_caller_identity.current.account_id}:cache-policy/*"
    ]
  }
}

resource "aws_iam_policy" "load_balancer" {
  name        = "${var.application}-${var.pipeline_name}-pipeline-load-balancer-access"
  path        = "/${var.application}/codebuild/"
  description = "Allow ${var.application} codebuild job to access load-balancer resources"
  policy      = data.aws_iam_policy_document.load_balancer.json
}

data "aws_iam_policy_document" "certificate" {
  statement {
    actions = [
      "acm:RequestCertificate",
      "acm:AddTagsToCertificate",
      "acm:DescribeCertificate",
      "acm:ListTagsForCertificate",
      "acm:DeleteCertificate"
    ]
    resources = [
      "arn:aws:acm:${local.account_region}:certificate/*"
    ]
  }

  statement {
    actions = [
      "acm:ListCertificates",
    ]
    resources = [
      "*"
    ]
  }
}

data "aws_iam_policy_document" "security_group" {
  statement {
    actions = [
      "ec2:CreateSecurityGroup",
      "ec2:CreateTags",
      "ec2:RevokeSecurityGroupEgress",
      "ec2:RevokeSecurityGroupIngress",
      "ec2:DeleteSecurityGroup",
      "ec2:AuthorizeSecurityGroupIngress",
      "ec2:AuthorizeSecurityGroupEgress"
    ]
    resources = [
      "arn:aws:ec2:${local.account_region}:security-group/*"
    ]
  }
}

data "aws_iam_policy_document" "ssm_parameter" {
  statement {
    actions = [
      "ssm:DescribeParameters"
    ]
    resources = [
      "arn:aws:ssm:${local.account_region}:*"
    ]
  }

  statement {
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
      "arn:aws:ssm:${local.account_region}:parameter/copilot/applications/${var.application}/*",
      "arn:aws:ssm:${local.account_region}:parameter/***"
    ]
  }
}

data "aws_iam_policy_document" "cloudwatch" {
  dynamic "statement" {
    for_each = local.environment_config
    content {
      actions = [
        "cloudwatch:GetDashboard",
        "cloudwatch:PutDashboard",
        "cloudwatch:DeleteDashboards"
      ]
      resources = [
        "arn:aws:cloudwatch::${data.aws_caller_identity.current.account_id}:dashboard/${var.application}-${statement.value.name}-compute"
      ]
    }
  }

  dynamic "statement" {
    for_each = local.environment_config
    content {
      actions = [
        "resource-groups:GetGroup",
        "resource-groups:CreateGroup",
        "resource-groups:Tag",
        "resource-groups:GetGroupQuery",
        "resource-groups:GetGroupConfiguration",
        "resource-groups:GetTags",
        "resource-groups:DeleteGroup"
      ]
      resources = [
        "arn:aws:resource-groups:${local.account_region}:group/${var.application}-${statement.value.name}-application-insights-resources"
      ]
    }
  }

  dynamic "statement" {
    for_each = local.environment_config
    content {
      actions = [
        "applicationinsights:CreateApplication",
        "applicationinsights:TagResource",
        "applicationinsights:DescribeApplication",
        "applicationinsights:ListTagsForResource",
        "applicationinsights:DeleteApplication"
      ]
      resources = [
        "arn:aws:applicationinsights:${local.account_region}:application/resource-group/${var.application}-${statement.value.name}-application-insights-resources"
      ]
    }
  }
}

data "aws_ssm_parameter" "log-destination-arn" {
  name = "/copilot/tools/central_log_groups"
}

data "aws_iam_policy_document" "logs" {
  statement {
    actions = [
      "logs:DescribeResourcePolicies",
      "logs:PutResourcePolicy",
      "logs:DeleteResourcePolicy",
      "logs:DescribeLogGroups"
    ]
    resources = [
      "arn:aws:logs:${local.account_region}:log-group::log-stream:"
    ]
  }

  statement {
    actions = [
      "logs:PutSubscriptionFilter"
    ]
    resources = [
      jsondecode(data.aws_ssm_parameter.log-destination-arn.value)["dev"],
      jsondecode(data.aws_ssm_parameter.log-destination-arn.value)["prod"]
    ]
  }

  statement {
    actions = [
      "logs:PutRetentionPolicy",
      "logs:ListTagsLogGroup",
      "logs:ListTagsForResource",
      "logs:DeleteLogGroup",
      "logs:CreateLogGroup",
      "logs:PutSubscriptionFilter",
      "logs:DescribeSubscriptionFilters",
      "logs:DeleteSubscriptionFilter",
      "logs:TagResource",
      "logs:AssociateKmsKey",
      "logs:DescribeLogStreams",
      "logs:DeleteLogStream"
    ]
    resources = [
      "arn:aws:logs:${local.account_region}:log-group:/aws/opensearch/*",
      "arn:aws:logs:${local.account_region}:log-group:/aws/rds/*",
      "arn:aws:logs:${local.account_region}:log-group:/aws/elasticache/*",
      "arn:aws:logs:${local.account_region}:log-group:codebuild/*"
    ]
  }
}

data "aws_iam_policy_document" "kms_key" {
  statement {
    actions = [
      "kms:CreateKey",
      "kms:ListAliases"
    ]
    resources = [
      "*"
    ]
  }

  statement {
    actions = [
      "kms:*"
    ]
    resources = [
      "arn:aws:kms:${local.account_region}:key/*"
    ]
  }

  statement {
    actions = [
      "kms:CreateAlias",
      "kms:DeleteAlias"
    ]
    resources = [
      "arn:aws:kms:${local.account_region}:alias/${var.application}-*"
    ]
  }
}

data "aws_iam_policy_document" "redis" {
  statement {
    actions = [
      "elasticache:CreateCacheSubnetGroup",
      "elasticache:AddTagsToResource",
      "elasticache:DescribeCacheSubnetGroups",
      "elasticache:ListTagsForResource",
      "elasticache:DeleteCacheSubnetGroup",
      "elasticache:CreateReplicationGroup"
    ]
    resources = [
      "arn:aws:elasticache:${local.account_region}:subnetgroup:*"
    ]
  }

  statement {
    actions = [
      "elasticache:AddTagsToResource",
      "elasticache:CreateReplicationGroup",
      "elasticache:DecreaseReplicaCount",
      "elasticache:DeleteReplicationGroup",
      "elasticache:DescribeReplicationGroups",
      "elasticache:IncreaseReplicaCount",
      "elasticache:ListTagsForResource",
      "elasticache:ModifyReplicationGroup",
    ]
    resources = [
      "arn:aws:elasticache:${local.account_region}:replicationgroup:*",
      "arn:aws:elasticache:${local.account_region}:parametergroup:*"
    ]
  }

  statement {
    actions = [
      "elasticache:DescribeCacheClusters"
    ]
    resources = [
      "arn:aws:elasticache:${local.account_region}:cluster:*"
    ]
  }

  statement {
    actions = [
      "elasticache:DescribeCacheEngineVersions"
    ]
    effect = "Allow"
    resources = [
      "*"
    ]
    sid = "AllowRedisListVersions"
  }
}

resource "aws_iam_policy" "redis" {
  name        = "${var.application}-${var.pipeline_name}-pipeline-redis-access"
  path        = "/${var.application}/codebuild/"
  description = "Allow ${var.application} codebuild job to access redis resources"
  policy      = data.aws_iam_policy_document.redis.json
}

data "aws_iam_policy_document" "postgres" {
  statement {
    actions = [
      "iam:PassRole"
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.application}-adminrole",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*-copy-pipeline-*"
    ]
  }

  dynamic "statement" {
    for_each = local.environment_config
    content {
      actions = [
        "iam:CreateRole",
        "iam:GetRole",
        "iam:ListRolePolicies",
        "iam:ListAttachedRolePolicies",
        "iam:ListInstanceProfilesForRole",
        "iam:DeleteRole",
        "iam:AttachRolePolicy",
        "iam:PutRolePolicy",
        "iam:GetRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:PassRole",
        "iam:UpdateAssumeRolePolicy",
        "iam:DetachRolePolicy"
      ]
      resources = [
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.application}-${statement.value.name}-*",
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/rds-enhanced-monitoring-*"
      ]
    }
  }

  dynamic "statement" {
    for_each = local.environment_config
    content {
      actions = [
        "lambda:GetFunction",
        "lambda:InvokeFunction",
        "lambda:ListVersionsByFunction",
        "lambda:GetFunctionCodeSigningConfig",
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration",
        "lambda:CreateFunction",
        "lambda:DeleteFunction"
      ]
      resources = [
        "arn:aws:lambda:${local.account_region}:function:${var.application}-${statement.value.name}-*"
      ]
    }
  }

  dynamic "statement" {
    for_each = local.environment_config
    content {
      actions = [
        "lambda:GetLayerVersion"
      ]
      resources = [
        "arn:aws:lambda:eu-west-2:763451185160:layer:python-postgres:1"
      ]
    }
  }

  dynamic "statement" {
    for_each = local.environment_config
    content {
      actions = [
        "rds:CreateDBParameterGroup",
        "rds:AddTagsToResource",
        "rds:ModifyDBParameterGroup",
        "rds:DescribeDBParameterGroups",
        "rds:DescribeDBParameters",
        "rds:ListTagsForResource",
        "rds:CreateDBInstance",
        "rds:ModifyDBInstance",
        "rds:DeleteDBParameterGroup"
      ]
      resources = [
        "arn:aws:rds:${local.account_region}:pg:${var.application}-${statement.value.name}-*"
      ]
    }
  }

  dynamic "statement" {
    for_each = local.environment_config
    content {
      actions = [
        "rds:CreateDBSubnetGroup",
        "rds:AddTagsToResource",
        "rds:DescribeDBSubnetGroups",
        "rds:ListTagsForResource",
        "rds:DeleteDBSubnetGroup",
        "rds:CreateDBInstance"
      ]
      resources = [
        "arn:aws:rds:${local.account_region}:subgrp:${var.application}-${statement.value.name}-*"
      ]
    }
  }

  statement {
    actions = [
      "rds:DescribeDBInstances"
    ]
    resources = [
      "arn:aws:rds:${local.account_region}:db:*"
    ]
  }

  dynamic "statement" {
    for_each = local.environment_config
    content {
      actions = [
        "rds:CreateDBInstance",
        "rds:AddTagsToResource",
        "rds:ModifyDBInstance"
      ]
      resources = [
        "arn:aws:rds:${local.account_region}:db:${var.application}-${statement.value.name}-*"
      ]
    }
  }

  statement {
    actions = [
      "secretsmanager:*",
      "kms:*"
    ]
    resources = [
      "arn:aws:secretsmanager:${local.account_region}:secret:rds*"
    ]
  }
}

resource "aws_iam_policy" "postgres" {
  name        = "${var.application}-${var.pipeline_name}-pipeline-postgres-access"
  path        = "/${var.application}/codebuild/"
  description = "Allow ${var.application} codebuild job to access postgres resources"
  policy      = data.aws_iam_policy_document.postgres.json
}

data "aws_iam_policy_document" "s3" {
  statement {
    actions = [
      "iam:ListAccountAliases"
    ]
    resources = [
      "*"
    ]
  }

  statement {
    actions = [
      "s3:*"
    ]
    resources = [
      "arn:aws:s3:::*"
    ]
  }
}

resource "aws_iam_policy" "s3" {
  name        = "${var.application}-${var.pipeline_name}-pipeline-s3-access"
  path        = "/${var.application}/codebuild/"
  description = "Allow ${var.application} codebuild job to access s3 resources"
  policy      = data.aws_iam_policy_document.s3.json
}

data "aws_iam_policy_document" "ecs" {
  statement {
    sid = "AllowTaskDefinitionsRead"
    actions = [
      "ecs:ListTaskDefinitionFamilies",
      "ecs:ListTaskDefinitions",
      "ecs:DescribeTaskDefinition",
    ]
    resources = ["*"]
  }

  statement {
    sid = "AllowRegister"
    actions = [
      "ecs:RegisterTaskDefinition",
    ]
    resources = [
      "arn:aws:ecs:${local.account_region}:task-definition/*",
      "arn:aws:ecs:${local.account_region}:task-definition/"
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
}

resource "aws_iam_policy" "ecs" {
  name        = "${var.application}-${var.pipeline_name}-pipeline-ecs-access"
  path        = "/${var.application}/codebuild/"
  description = "Allow ${var.application} codebuild job to access ecs resources"
  policy      = data.aws_iam_policy_document.ecs.json
}

data "aws_iam_policy_document" "opensearch" {
  statement {
    actions = [
      "es:CreateElasticsearchDomain",
      "es:AddTags",
      "es:DescribeDomain",
      "es:DescribeDomainConfig",
      "es:ListTags",
      "es:DeleteDomain",
      "es:UpdateDomainConfig"
    ]
    resources = [
      "arn:aws:es:${local.account_region}:domain/*"
    ]
  }

  statement {
    actions = [
      "es:ListVersions"
    ]
    effect = "Allow"
    resources = [
      "*"
    ]
    sid = "AllowOpensearchListVersions"
  }
}

resource "aws_iam_policy" "opensearch" {
  name        = "${var.application}-${var.pipeline_name}-pipeline-opensearch-access"
  path        = "/${var.application}/codebuild/"
  description = "Allow ${var.application} codebuild job to access opensearch resources"
  policy      = data.aws_iam_policy_document.opensearch.json
}

data "aws_iam_policy_document" "origin_secret_rotate_access" {
  statement {
    effect = "Allow"
    actions = [
      "lambda:GetPolicy",
      "lambda:RemovePermission",
      "lambda:DeleteFunction",
      "lambda:TagResource",
      "lambda:PutFunctionConcurrency",
      "lambda:AddPermission",
      "lambda:DeleteFunction"
    ]
    resources = [
      for env in local.environment_config : "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:${var.application}-${env.name}-origin-secret-rotate"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "lambda:GetLayerVersion"
    ]
    resources = [
      "arn:aws:lambda:eu-west-2:763451185160:layer:python-requests:1"
    ]
  }

  statement {
    sid    = "WAFv2ReadAccess"
    effect = "Allow"
    actions = [
      "wafv2:GetWebACL",
      "wafv2:GetWebACLForResource",
      "wafv2:ListTagsForResource",
      "wafv2:DeleteWebACL",
      "wafv2:CreateWebACL",
      "wafv2:TagResource",
      "wafv2:AssociateWebACL"
    ]
    resources = [
      "arn:aws:wafv2:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:regional/webacl/*/*"
    ]
  }

  statement {
    sid    = "WAFv2RuleSetAccess"
    effect = "Allow"
    actions = [
      "wafv2:CreateWebACL"
    ]
    resources = [
      "arn:aws:wafv2:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:regional/managedruleset/*/*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:DescribeSecret",
      "secretsmanager:GetSecretValue",
      "secretsmanager:GetResourcePolicy",
      "secretsmanager:DeleteResourcePolicy",
      "secretsmanager:CancelRotateSecret",
      "secretsmanager:DeleteSecret",
      "secretsmanager:CreateSecret",
      "secretsmanager:TagResource",
      "secretsmanager:PutResourcePolicy",
      "secretsmanager:PutSecretValue",
      "secretsmanager:RotateSecret"
    ]
    resources = [
      for env in local.environment_config : "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.application}-${env.name}-origin-verify-header-secret-*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "iam:TagRole"
    ]
    resources = [
      for env in local.environment_config : "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.application}-${env.name}-origin-secret-rotate-role"
    ]
  }
}

resource "aws_iam_policy" "origin_secret_rotate_access" {
  name        = "${var.application}-${var.pipeline_name}-pipeline-origin-secret-rotate-access"
  path        = "/${var.application}/codebuild/"
  description = "Allow ${var.application} codebuild job to access lambda resources"
  policy      = data.aws_iam_policy_document.origin_secret_rotate_access.json
}

# Policies for AWS Copilot
data "aws_iam_policy_document" "copilot_assume_role" {
  dynamic "statement" {
    for_each = local.environment_config
    content {
      actions = [
        "sts:AssumeRole"
      ]
      resources = [
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.application}-${statement.value.name}-EnvManagerRole"
      ]
    }
  }

  dynamic "statement" {
    for_each = toset(local.triggers_another_pipeline ? local.triggered_pipeline_environments : [])
    content {
      actions = [
        "sts:AssumeRole"
      ]
      resources = [
        "arn:aws:iam::${local.triggered_account_id}:role/${var.application}-${statement.value.name}-EnvManagerRole"
      ]
    }
  }
}

data "aws_iam_policy_document" "cloudformation" {
  statement {
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
    actions = [
      "cloudformation:ListExports"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "cloudformation" {
  name        = "${var.application}-${var.pipeline_name}-pipeline-cloudformation-access"
  path        = "/${var.application}/codebuild/"
  description = "Allow ${var.application} codebuild job to access cloudformation resources"
  policy      = data.aws_iam_policy_document.cloudformation.json
}

data "aws_iam_policy_document" "iam" {
  dynamic "statement" {
    for_each = local.environment_config
    content {
      actions = [
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:CreatePolicy",
        "iam:DeletePolicy",
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:TagRole",
        "iam:PutRolePolicy",
        "iam:GetRole",
        "iam:ListRolePolicies",
        "iam:GetRolePolicy",
        "iam:ListAttachedRolePolicies",
        "iam:ListInstanceProfilesForRole",
        "iam:DeleteRolePolicy",
        "iam:UpdateAssumeRolePolicy",
        "iam:TagRole"
      ]
      resources = [
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*-${var.application}-*-conduitEcsTask",
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.application}-${statement.value.name}-CFNExecutionRole",
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.application}-${statement.value.name}-EnvManagerRole",
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*-S3MigrationRole",
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.application}-*-exec",
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.application}-*-task",
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*-copy-pipeline-*",
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.application}-${statement.value.name}-codebase-pipeline-deploy"
      ]
    }
  }

  statement {
    actions = [
      "sts:AssumeRole"
    ]
    resources = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.application}-${var.pipeline_name}-environment-pipeline-codebuild"]
  }

  statement {
    sid = "AllowUpdatingSharedS3MigrationRoleTrustPolicy"
    actions = [
      "iam:UpdateAssumeRolePolicy"
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*-S3MigrationRole"
    ]
  }

  statement {
    sid = "AllowUpdatingPostgresLambdaRoleTrustPolicy"
    actions = [
      "iam:UpdateAssumeRolePolicy"
    ]
    resources = [for environment in local.environment_config : "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.application}-${environment.name}-*-lambda-role"]
  }
}

data "aws_iam_policy_document" "codepipeline" {
  statement {
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

  statement {
    actions = [
      "codepipeline:CreatePipeline",
      "codepipeline:DeletePipeline",
      "codepipeline:GetPipeline",
      "codepipeline:UpdatePipeline",
      "codepipeline:ListTagsForResource",
      "codepipeline:TagResource"
    ]
    resources = [
      "arn:aws:codepipeline:${local.account_region}:*-copy-pipeline",
      "arn:aws:codepipeline:${local.account_region}:*-copy-pipeline/*"
    ]
  }

  statement {
    actions = [
      "codebuild:CreateProject",
      "codebuild:BatchGetProjects",
      "codebuild:DeleteProject",
      "codebuild:UpdateProject"
    ]
    resources = [
      "arn:aws:codebuild:${local.account_region}:project/*"
    ]
  }

  statement {
    actions = [
      "scheduler:CreateSchedule",
      "scheduler:UpdateSchedule",
      "scheduler:DeleteSchedule",
      "scheduler:TagResource",
      "scheduler:GetSchedule",
      "scheduler:ListSchedules",
      "scheduler:ListTagsForResource"
    ]
    resources = [
      "arn:aws:scheduler:${local.account_region}:schedule/*"
    ]
  }
}

resource "aws_iam_policy" "iam" {
  name        = "${var.application}-${var.pipeline_name}-pipeline-iam"
  path        = "/${var.application}/codebuild/"
  description = "Allow ${var.application} codebuild job to manage roles"
  policy      = data.aws_iam_policy_document.iam.json
}

resource "aws_iam_policy" "codepipeline" {
  name        = "${var.application}-${var.pipeline_name}-pipeline-codepipeline"
  path        = "/${var.application}/codebuild/"
  description = "Allow ${var.application} codebuild job to codepipelines"
  policy      = data.aws_iam_policy_document.codepipeline.json
}

# Roles
resource "aws_iam_role" "environment_pipeline_codepipeline" {
  name               = "${var.application}-${var.pipeline_name}-environment-pipeline-codepipeline"
  assume_role_policy = data.aws_iam_policy_document.assume_codepipeline_role.json
  tags               = local.tags
}

resource "aws_iam_role" "environment_pipeline_codebuild" {
  name               = "${var.application}-${var.pipeline_name}-environment-pipeline-codebuild"
  assume_role_policy = data.aws_iam_policy_document.assume_codebuild_role.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "attach_iam_policy" {
  role       = aws_iam_role.environment_pipeline_codebuild.name
  policy_arn = aws_iam_policy.iam.arn
}

resource "aws_iam_role_policy_attachment" "attach_cloudformation_policy" {
  role       = aws_iam_role.environment_pipeline_codebuild.name
  policy_arn = aws_iam_policy.cloudformation.arn
}

resource "aws_iam_role_policy_attachment" "attach_codepipeline_policy" {
  role       = aws_iam_role.environment_pipeline_codebuild.name
  policy_arn = aws_iam_policy.codepipeline.arn
}

resource "aws_iam_role_policy_attachment" "attach_redis_policy" {
  role       = aws_iam_role.environment_pipeline_codebuild.name
  policy_arn = aws_iam_policy.redis.arn
}

resource "aws_iam_role_policy_attachment" "attach_postgres_policy" {
  role       = aws_iam_role.environment_pipeline_codebuild.name
  policy_arn = aws_iam_policy.postgres.arn
}

resource "aws_iam_role_policy_attachment" "attach_opensearch_policy" {
  role       = aws_iam_role.environment_pipeline_codebuild.name
  policy_arn = aws_iam_policy.opensearch.arn
}

resource "aws_iam_role_policy_attachment" "attach_load_balancer_policy" {
  role       = aws_iam_role.environment_pipeline_codebuild.name
  policy_arn = aws_iam_policy.load_balancer.arn
}

resource "aws_iam_role_policy_attachment" "attach_s3_policy" {
  role       = aws_iam_role.environment_pipeline_codebuild.name
  policy_arn = aws_iam_policy.s3.arn
}

resource "aws_iam_role_policy_attachment" "attach_ecs_policy" {
  role       = aws_iam_role.environment_pipeline_codebuild.name
  policy_arn = aws_iam_policy.ecs.arn
}

resource "aws_iam_role_policy_attachment" "attach_origin_secret_rotate_policy" {
  role       = aws_iam_role.environment_pipeline_codebuild.name
  policy_arn = aws_iam_policy.origin_secret_rotate_access.arn
}

# Inline policies
resource "aws_iam_role_policy" "artifact_store_access_for_environment_codepipeline" {
  name   = "${var.application}-${var.pipeline_name}-artifact-store-access-for-environment-codepipeline"
  role   = aws_iam_role.environment_pipeline_codepipeline.name
  policy = data.aws_iam_policy_document.access_artifact_store.json
}

resource "aws_iam_role_policy" "artifact_store_access_for_environment_codebuild" {
  name   = "${var.application}-${var.pipeline_name}-artifact-store-access-for-environment-codebuild"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.access_artifact_store.json
}

resource "aws_iam_role_policy" "log_access_for_environment_codebuild" {
  name   = "${var.application}-${var.pipeline_name}-log-access-for-environment-codebuild"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.write_environment_pipeline_codebuild_logs.json
}

# Terraform state access
resource "aws_iam_role_policy" "state_bucket_access_for_environment_codebuild" {
  name   = "${var.application}-${var.pipeline_name}-state-bucket-access-for-environment-codebuild"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.state_bucket_access.json
}

resource "aws_iam_role_policy" "state_kms_key_access_for_environment_codebuild" {
  name   = "${var.application}-${var.pipeline_name}-state-kms-key-access-for-environment-codebuild"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.state_kms_key_access.json
}

resource "aws_iam_role_policy" "state_dynamo_db_access_for_environment_codebuild" {
  name   = "${var.application}-${var.pipeline_name}-state-dynamo-db-access-for-environment-codebuild"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.state_dynamo_db_access.json
}

# VPC and Subnets
resource "aws_iam_role_policy" "ec2_read_access_for_environment_codebuild" {
  name   = "${var.application}-${var.pipeline_name}-ec2-read-access-for-environment-codebuild"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.ec2_read_access.json
}

resource "aws_iam_role_policy" "ssm_read_access_for_environment_codebuild" {
  name   = "${var.application}-${var.pipeline_name}-ssm-read-access-for-environment-codebuild"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.ssm_read_access.json
}

# Assume DNS account role
resource "aws_iam_role_policy" "dns_account_assume_role_for_environment_codebuild" {
  name   = "${var.application}-${var.pipeline_name}-dns-account-assume-role-for-environment-codebuild"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.dns_account_assume_role.json
}

resource "aws_iam_role_policy" "certificate_for_environment_codebuild" {
  name   = "${var.application}-${var.pipeline_name}-certificate-for-environment-codebuild"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.certificate.json
}

resource "aws_iam_role_policy" "security_group_for_environment_codebuild" {
  name   = "${var.application}-${var.pipeline_name}-security-group-for-environment-codebuild"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.security_group.json
}

resource "aws_iam_role_policy" "ssm_parameter_for_environment_codebuild" {
  name   = "${var.application}-${var.pipeline_name}-ssm-parameter-for-environment-codebuild"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.ssm_parameter.json
}

resource "aws_iam_role_policy" "cloudwatch_for_environment_codebuild" {
  name   = "${var.application}-${var.pipeline_name}-cloudwatch-for-environment-codebuild"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.cloudwatch.json
}

resource "aws_iam_role_policy" "logs_for_environment_codebuild" {
  name   = "${var.application}-${var.pipeline_name}-logs-for-environment-codebuild"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.logs.json
}

resource "aws_iam_role_policy" "kms_key_for_environment_codebuild" {
  name   = "${var.application}-${var.pipeline_name}-kms-key-for-environment-codebuild"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.kms_key.json
}

resource "aws_iam_role_policy" "copilot_assume_role_for_environment_codebuild" {
  name   = "${var.application}-${var.pipeline_name}-copilot-assume-role-for-environment-codebuild"
  role   = aws_iam_role.environment_pipeline_codebuild.name
  policy = data.aws_iam_policy_document.copilot_assume_role.json
}

########### TRIGGERED PIPELINE RESOURCES ##########

#------PROD-TARGET-ACCOUNT------
resource "aws_iam_role" "trigger_pipeline" {
  for_each           = local.set_of_triggering_pipeline_names
  name               = "${var.application}-${var.pipeline_name}-trigger-pipeline-from-${each.value}"
  assume_role_policy = data.aws_iam_policy_document.assume_trigger_pipeline.json
  tags               = local.tags
}

data "aws_iam_policy_document" "assume_trigger_pipeline" {
  statement {
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = local.triggering_pipeline_role_arns
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role_policy" "trigger_pipeline" {
  for_each = local.set_of_triggering_pipeline_names
  name     = "${var.application}-${var.pipeline_name}-trigger-pipeline-from-${each.value}"
  role     = aws_iam_role.trigger_pipeline[each.value].name
  policy   = data.aws_iam_policy_document.trigger_pipeline[each.value].json
}

data "aws_iam_policy_document" "trigger_pipeline" {
  for_each = local.set_of_triggering_pipeline_names
  statement {
    actions = [
      "codepipeline:StartPipelineExecution",
    ]
    resources = [
      aws_codepipeline.environment_pipeline.arn
    ]
  }
}

resource "aws_iam_role_policy" "assume_role_for_copilot_env_commands" {
  for_each = toset(local.triggered_by_another_pipeline ? [""] : [])
  name     = "${var.application}-${var.pipeline_name}-assume-role-for-copilot-env-commands"
  role     = aws_iam_role.environment_pipeline_codebuild.name
  policy   = data.aws_iam_policy_document.assume_role_for_copilot_env_commands_policy_document[""].json
}

data "aws_iam_policy_document" "assume_role_for_copilot_env_commands_policy_document" {
  for_each = toset(local.triggered_by_another_pipeline ? [""] : [])
  statement {
    actions = [
      "sts:AssumeRole"
    ]
    resources = local.triggering_pipeline_role_arns
  }

  statement {
    actions = [
      "kms:*",
    ]
    resources = [
      "arn:aws:kms:${data.aws_region.current.name}:${local.triggering_account_id}:key/*"
    ]
  }

  statement {
    actions = [
      "s3:*",
    ]
    resources = [
      "arn:aws:s3:::stackset-${var.application}-*-pipelinebuiltartifactbuc-*"
    ]
  }
}

#------NON-PROD-SOURCE-ACCOUNT------

resource "aws_iam_role_policy" "assume_role_to_trigger_pipeline_policy" {
  for_each = toset(local.triggers_another_pipeline ? [""] : [])
  name     = "${var.application}-${var.pipeline_name}-assume-role-to-trigger-codepipeline-policy"
  role     = aws_iam_role.environment_pipeline_codebuild.name
  policy   = data.aws_iam_policy_document.assume_role_to_trigger_codepipeline_policy_document[""].json
}

data "aws_iam_policy_document" "assume_role_to_trigger_codepipeline_policy_document" {
  for_each = toset(local.triggers_another_pipeline ? [""] : [])
  statement {
    actions = [
      "sts:AssumeRole"
    ]
    resources = [local.triggered_pipeline_account_role]
  }
}
