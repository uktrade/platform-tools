resource "aws_iam_role" "environment_pipeline_deploy" {
  name               = "${var.args.application}-${var.environment}-environment-pipeline-deploy"
  assume_role_policy = data.aws_iam_policy_document.assume_environment_pipeline.json
  tags               = local.tags
}

data "aws_iam_policy_document" "assume_environment_pipeline" {
  statement {
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${local.pipeline_account_id}:root"]
    }
    condition {
      test = "ArnLike"
      values = [
        "arn:aws:iam::${local.pipeline_account_id}:role/${var.args.application}-*-environment-*"
      ]
      variable = "aws:PrincipalArn"
    }
    actions = ["sts:AssumeRole"]
  }
}

# Terraform state
data "aws_s3_bucket" "state_bucket" {
  bucket = "terraform-platform-state-${local.deploy_account_name}"
}
data "aws_kms_key" "state_kms_key" {
  key_id = "alias/terraform-platform-state-s3-key-${local.deploy_account_name}"
}

resource "aws_iam_role_policy" "terraform_state_access" {
  name   = "terraform-state-access"
  role   = aws_iam_role.environment_pipeline_deploy.name
  policy = data.aws_iam_policy_document.terraform_state_access.json
}

data "aws_iam_policy_document" "terraform_state_access" {
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

  statement {
    actions = [
      "dynamodb:DescribeTable",
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:DeleteItem"
    ]
    resources = [
      "arn:aws:dynamodb:${local.account_region}:table/terraform-platform-lockdb-${local.deploy_account_name}"
    ]
  }
}

# VPC
resource "aws_iam_role_policy" "vpc_access" {
  name   = "vpc-access"
  role   = aws_iam_role.environment_pipeline_deploy.name
  policy = data.aws_iam_policy_document.vpc_access.json
}

data "aws_iam_policy_document" "vpc_access" {
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

# ALB and CDN
resource "aws_iam_role_policy" "alb_cdn_cert_access" {
  name   = "alb-cdn-cert-access"
  role   = aws_iam_role.environment_pipeline_deploy.name
  policy = data.aws_iam_policy_document.alb_cdn_cert_access.json
}

data "aws_iam_policy_document" "alb_cdn_cert_access" {
  statement {
    actions = [
      "sts:AssumeRole"
    ]
    resources = ["arn:aws:iam::${local.dns_account_id}:role/environment-pipeline-assumed-role"]
  }

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

  statement {
    actions = [
      "elasticloadbalancing:CreateTargetGroup",
      "elasticloadbalancing:AddTags",
      "elasticloadbalancing:ModifyTargetGroupAttributes",
      "elasticloadbalancing:DeleteTargetGroup"
    ]
    resources = [
      "arn:aws:elasticloadbalancing:${local.account_region}:targetgroup/${var.args.application}-${var.environment}-http/*"
    ]
  }

  statement {
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
      "arn:aws:elasticloadbalancing:${local.account_region}:loadbalancer/app/${var.args.application}-${var.environment}/*"
    ]
  }

  statement {
    actions = [
      "elasticloadbalancing:AddTags",
      "elasticloadbalancing:ModifyListener"
    ]
    resources = [
      "arn:aws:elasticloadbalancing:${local.account_region}:listener/app/${var.args.application}-${var.environment}/*"
    ]
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

  # Origin secret rotate
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
    resources = ["arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:${var.args.application}-${var.environment}-origin-secret-rotate"]
  }

  statement {
    sid    = "LambdaLayerAccess"
    effect = "Allow"
    actions = [
      "lambda:GetLayerVersion"
    ]
    resources = [
      "arn:aws:lambda:eu-west-2:763451185160:layer:python-requests:8"
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
    resources = ["arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.args.application}-${var.environment}-origin-verify-header-secret-*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "iam:TagRole"
    ]
    resources = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.args.application}-${var.environment}-origin-secret-rotate-role"]
  }
}

# SSM
data "aws_ssm_parameter" "central_log_group_parameter" {
  name = "/copilot/tools/central_log_groups"
}

resource "aws_iam_role_policy" "ssm_access" {
  name   = "ssm-access"
  role   = aws_iam_role.environment_pipeline_deploy.name
  policy = data.aws_iam_policy_document.ssm_access.json
}

data "aws_iam_policy_document" "ssm_access" {
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
      "arn:aws:ssm:${local.account_region}:parameter/copilot/${var.args.application}/*/secrets/*",
      "arn:aws:ssm:${local.account_region}:parameter/copilot/applications/${var.args.application}",
      "arn:aws:ssm:${local.account_region}:parameter/copilot/applications/${var.args.application}/*",
      "arn:aws:ssm:${local.account_region}:parameter/***"
    ]
  }

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

# Logs
resource "aws_iam_role_policy" "logs_access" {
  name   = "logs-access"
  role   = aws_iam_role.environment_pipeline_deploy.name
  policy = data.aws_iam_policy_document.logs_access.json
}

data "aws_iam_policy_document" "logs_access" {
  statement {
    actions = [
      "cloudwatch:GetDashboard",
      "cloudwatch:PutDashboard",
      "cloudwatch:DeleteDashboards"
    ]
    resources = [
      "arn:aws:cloudwatch::${data.aws_caller_identity.current.account_id}:dashboard/${var.args.application}-${var.environment}-compute"
    ]
  }

  statement {
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
      "arn:aws:resource-groups:${local.account_region}:group/${var.args.application}-${var.environment}-application-insights-resources"
    ]
  }

  statement {
    actions = [
      "applicationinsights:CreateApplication",
      "applicationinsights:TagResource",
      "applicationinsights:DescribeApplication",
      "applicationinsights:ListTagsForResource",
      "applicationinsights:DeleteApplication"
    ]
    resources = [
      "arn:aws:applicationinsights:${local.account_region}:application/resource-group/${var.args.application}-${var.environment}-application-insights-resources"
    ]
  }

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
      jsondecode(data.aws_ssm_parameter.central_log_group_parameter.value)["dev"],
      jsondecode(data.aws_ssm_parameter.central_log_group_parameter.value)["prod"]
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
      "arn:aws:logs:${local.account_region}:log-group:codebuild/*",
      "arn:aws:logs:${local.account_region}:log-group:/conduit/*"
    ]
  }
}

# KMS
resource "aws_iam_role_policy" "kms_key_access" {
  name   = "kms-key-access"
  role   = aws_iam_role.environment_pipeline_deploy.name
  policy = data.aws_iam_policy_document.kms_key_access.json
}

data "aws_iam_policy_document" "kms_key_access" {
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
      "arn:aws:kms:${local.account_region}:alias/${var.args.application}-*"
    ]
  }
}

# Redis
resource "aws_iam_role_policy" "redis_access" {
  name   = "redis-access"
  role   = aws_iam_role.environment_pipeline_deploy.name
  policy = data.aws_iam_policy_document.redis_access.json
}

data "aws_iam_policy_document" "redis_access" {
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

# Postgres
resource "aws_iam_role_policy" "postgres_access" {
  name   = "postgres-access"
  role   = aws_iam_role.environment_pipeline_deploy.name
  policy = data.aws_iam_policy_document.postgres_access.json
}

data "aws_iam_policy_document" "postgres_access" {
  statement {
    actions = [
      "iam:PassRole"
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.args.application}-adminrole",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*-copy-pipeline-*"
    ]
  }

  statement {
    actions = [
      "iam:*"
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.args.application}-${var.environment}-*",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/rds-enhanced-monitoring-*"
    ]
  }

  statement {
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
      "arn:aws:lambda:${local.account_region}:function:${var.args.application}-${var.environment}-*"
    ]
  }

  statement {
    actions = [
      "lambda:GetLayerVersion"
    ]
    resources = [
      "arn:aws:lambda:eu-west-2:763451185160:layer:python-postgres:1"
    ]
  }

  statement {
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
      "arn:aws:rds:${local.account_region}:pg:${var.args.application}-${var.environment}-*"
    ]
  }

  statement {
    actions = [
      "rds:CreateDBSubnetGroup",
      "rds:AddTagsToResource",
      "rds:DescribeDBSubnetGroups",
      "rds:ListTagsForResource",
      "rds:DeleteDBSubnetGroup",
      "rds:CreateDBInstance"
    ]
    resources = [
      "arn:aws:rds:${local.account_region}:subgrp:${var.args.application}-${var.environment}-*"
    ]
  }

  statement {
    actions = [
      "rds:DescribeDBInstances"
    ]
    resources = [
      "arn:aws:rds:${local.account_region}:db:*"
    ]
  }

  statement {
    actions = [
      "rds:CreateDBInstance",
      "rds:AddTagsToResource",
      "rds:ModifyDBInstance"
    ]
    resources = [
      "arn:aws:rds:${local.account_region}:db:${var.args.application}-${var.environment}-*"
    ]
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

# S3
resource "aws_iam_role_policy" "s3_access" {
  name   = "s3-access"
  role   = aws_iam_role.environment_pipeline_deploy.name
  policy = data.aws_iam_policy_document.s3_access.json
}

data "aws_iam_policy_document" "s3_access" {
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

# ECS for data copy
resource "aws_iam_role_policy" "ecs_access" {
  name   = "ecs-access"
  role   = aws_iam_role.environment_pipeline_deploy.name
  policy = data.aws_iam_policy_document.ecs_access.json
}

data "aws_iam_policy_document" "ecs_access" {
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

# Opensearch
resource "aws_iam_role_policy" "opensearch_access" {
  name   = "opensearch-access"
  role   = aws_iam_role.environment_pipeline_deploy.name
  policy = data.aws_iam_policy_document.opensearch_access.json
}

data "aws_iam_policy_document" "opensearch_access" {
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

# Copilot
resource "aws_iam_role_policy" "copilot_access" {
  name   = "copilot-access"
  role   = aws_iam_role.environment_pipeline_deploy.name
  policy = data.aws_iam_policy_document.copilot_access.json
}

data "aws_iam_policy_document" "copilot_access" {
  statement {
    actions = [
      "sts:AssumeRole"
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.args.application}-${var.environment}-EnvManagerRole"
    ]
  }

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
      "arn:aws:cloudformation:${local.account_region}:stack/${var.args.application}-*",
      "arn:aws:cloudformation:${local.account_region}:stack/StackSet-${var.args.application}-infrastructure-*",
      "arn:aws:cloudformation:${local.account_region}:stackset/${var.args.application}-infrastructure:*",
    ]
  }

  statement {
    actions = [
      "cloudformation:ListExports"
    ]
    resources = ["*"]
  }
}

# IAM
resource "aws_iam_role_policy" "iam_access" {
  name   = "iam-access"
  role   = aws_iam_role.environment_pipeline_deploy.name
  policy = data.aws_iam_policy_document.iam_access.json
}

data "aws_iam_policy_document" "iam_access" {
  statement {
    actions = [
      "iam:*"
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*-${var.args.application}-*-conduitEcsTask",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.args.application}-${var.environment}-CFNExecutionRole",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.args.application}-${var.environment}-EnvManagerRole",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*-S3MigrationRole",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.args.application}-*-exec",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.args.application}-*-task",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*-copy-pipeline-*",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.args.application}-${var.environment}-codebase-pipeline-deploy",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.args.application}-${var.environment}-*-conduit-task-role",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.args.application}-${var.environment}-*-conduit-exec-role",
    ]
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
    resources = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.args.application}-${var.environment}-*-lambda-role"]
  }
}

# Codepipeline
resource "aws_iam_role_policy" "codepipeline_access" {
  name   = "codepipeline-access"
  role   = aws_iam_role.environment_pipeline_deploy.name
  policy = data.aws_iam_policy_document.codepipeline_access.json
}

data "aws_iam_policy_document" "codepipeline_access" {
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
