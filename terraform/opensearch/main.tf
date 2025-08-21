data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "aws_kms_key" "cloudwatch_log_group_kms_key" {
  description         = "KMS Key for ${var.name}-${var.environment} CloudWatch Log encryption"
  enable_key_rotation = true
  tags                = local.tags
}

resource "aws_kms_key_policy" "opensearch_to_cloudwatch" {
  key_id = aws_kms_key.cloudwatch_log_group_kms_key.key_id
  policy = jsonencode({
    Id = "OpenSearchToCloudWatch"
    Statement = [
      {
        "Sid" : "Enable IAM User Permissions",
        "Effect" : "Allow",
        "Principal" : {
          "AWS" : "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        },
        "Action" : "kms:*",
        "Resource" : "*"
      },
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "logs.${data.aws_region.current.region}.amazonaws.com"
        },
        "Action" : "kms:*",
        "Resource" : "*"
      }
    ]
    Version = "2012-10-17"
  })
}

resource "aws_cloudwatch_log_group" "opensearch_log_group_index_slow_logs" {
  name              = "/aws/opensearch/${local.domain_name}/index-slow"
  retention_in_days = coalesce(var.config.index_slow_log_retention_in_days, 7)
  kms_key_id        = aws_kms_key.cloudwatch_log_group_kms_key.arn
}

resource "aws_cloudwatch_log_group" "opensearch_log_group_search_slow_logs" {
  name              = "/aws/opensearch/${local.domain_name}/search-slow"
  retention_in_days = coalesce(var.config.search_slow_log_retention_in_days, 7)
  kms_key_id        = aws_kms_key.cloudwatch_log_group_kms_key.arn
}

resource "aws_cloudwatch_log_group" "opensearch_log_group_es_application_logs" {
  name              = "/aws/opensearch/${local.domain_name}/es-application"
  retention_in_days = coalesce(var.config.es_app_log_retention_in_days, 7)
  kms_key_id        = aws_kms_key.cloudwatch_log_group_kms_key.arn
}

resource "aws_cloudwatch_log_group" "opensearch_log_group_audit_logs" {
  name              = "/aws/opensearch/${local.domain_name}/audit"
  retention_in_days = coalesce(var.config.audit_log_retention_in_days, 7)
  kms_key_id        = aws_kms_key.cloudwatch_log_group_kms_key.arn
}

resource "aws_security_group" "opensearch-security-group" {
  # checkov:skip=CKV2_AWS_5: False Positive in Checkov - https://github.com/bridgecrewio/checkov/issues/3010
  name        = local.domain_name
  vpc_id      = data.aws_vpc.vpc.id
  description = "Allow inbound HTTP traffic"

  ingress {
    description = "HTTP from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"

    cidr_blocks = [
      data.aws_vpc.vpc.cidr_block,
    ]
  }

  egress {
    description = "Allow traffic out on all ports"
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"

    cidr_blocks = [
      "0.0.0.0/0"
    ]
  }
  tags = local.tags
}

resource "random_password" "password" {
  length           = 32
  upper            = true
  special          = true
  lower            = true
  numeric          = true
  min_upper        = 1
  min_special      = 1
  min_lower        = 1
  min_numeric      = 1
  override_special = coalesce(var.config.password_special_characters, "-_!.~$&'()*+,;=")
}

resource "aws_opensearch_domain" "this" {
  # checkov:skip=CKV_AWS_247: Enabling CMK Forces Cluster Recreation. To be implemented as a separate breaking change
  # checkov:skip=CKV2_AWS_59: This is a configurable option not picked up by Checkov as it's variablised
  domain_name    = local.domain_name
  engine_version = "OpenSearch_${var.config.engine}"

  depends_on = [
    aws_cloudwatch_log_group.opensearch_log_group_index_slow_logs,
    aws_cloudwatch_log_group.opensearch_log_group_search_slow_logs,
    aws_cloudwatch_log_group.opensearch_log_group_es_application_logs,
    aws_cloudwatch_log_group.opensearch_log_group_audit_logs
  ]

  cluster_config {
    # checkov:skip=CKV_AWS_318: Checkov is not clever enough to recognise the null in this conditional
    dedicated_master_count   = var.config.enable_ha ? 3 : null
    dedicated_master_type    = var.config.enable_ha ? var.config.instance : null
    dedicated_master_enabled = var.config.enable_ha
    instance_type            = var.config.instance
    instance_count           = local.instances
    zone_awareness_enabled   = var.config.enable_ha
    dynamic "zone_awareness_config" {
      for_each = var.config.enable_ha ? [1] : []
      content {
        availability_zone_count = local.zone_count

      }
    }
  }

  advanced_security_options {
    enabled                        = true
    anonymous_auth_enabled         = false
    internal_user_database_enabled = true
    master_user_options {
      master_user_name     = local.master_user
      master_user_password = random_password.password.result
    }
  }

  encrypt_at_rest {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  ebs_options {
    ebs_enabled = true
    volume_size = var.config.volume_size
    volume_type = coalesce(var.config.ebs_volume_type, "gp2")
    throughput  = var.config.ebs_volume_type == "gp3" ? coalesce(var.config.ebs_throughput, 250) : null
  }

  auto_tune_options {
    desired_state       = local.auto_tune_desired_state
    rollback_on_disable = local.auto_tune_rollback_on_disable
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch_log_group_index_slow_logs.arn
    log_type                 = "INDEX_SLOW_LOGS"
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch_log_group_search_slow_logs.arn
    log_type                 = "SEARCH_SLOW_LOGS"
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch_log_group_es_application_logs.arn
    log_type                 = "ES_APPLICATION_LOGS"
  }

  log_publishing_options {
    cloudwatch_log_group_arn = aws_cloudwatch_log_group.opensearch_log_group_audit_logs.arn
    log_type                 = "AUDIT_LOGS"
    enabled                  = true
  }

  node_to_node_encryption {
    enabled = true
  }

  vpc_options {
    subnet_ids         = local.subnets
    security_group_ids = [aws_security_group.opensearch-security-group.id]
  }

  access_policies = <<CONFIG
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": "es:*",
            "Principal": "*",
            "Effect": "Allow",
            "Resource": "arn:aws:es:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:domain/${local.domain_name}/*"
        }
    ]
}
CONFIG

  tags = local.tags
}

resource "aws_ssm_parameter" "opensearch_endpoint" {
  name        = local.ssm_parameter_name
  description = "opensearch_password"
  type        = "SecureString"
  value       = "https://${local.master_user}:${local.urlencode_password ? urlencode(random_password.password.result) : random_password.password.result}@${aws_opensearch_domain.this.endpoint}"
  key_id      = aws_kms_key.ssm_opensearch_endpoint.arn

  tags = local.tags
}
resource "aws_kms_key" "ssm_opensearch_endpoint" {
  # checkov:skip=CKV2_AWS_64:skipping pending discussion with rest of team on the policy
  description             = "KMS key for ${var.name}-${var.application}-${var.environment}-opensearch-cluster SSM parameters"
  deletion_window_in_days = 10
  enable_key_rotation     = true

  tags = local.tags
}

resource "aws_iam_role" "conduit_ecs_task_role" {
  name               = "${var.name}-${var.application}-${var.environment}-conduitEcsTask"
  assume_role_policy = data.aws_iam_policy_document.assume_ecstask_role.json

  tags = local.tags
}

data "aws_iam_policy_document" "assume_ecstask_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role_policy" "kms_access_for_conduit_ecs_task" {
  name   = "AllowReadingofCMKSecrets"
  role   = aws_iam_role.conduit_ecs_task_role.name
  policy = data.aws_iam_policy_document.access_ssm_with_kms.json
}

data "aws_iam_policy_document" "access_ssm_with_kms" {
  statement {
    actions = [
      "kms:Decrypt",
      "ssm:GetParameters",
      "logs:CreateLogStream"
    ]
    effect = "Allow"
    resources = [
      aws_kms_key.ssm_opensearch_endpoint.arn,
      aws_ssm_parameter.opensearch_endpoint.arn,
      "arn:aws:logs:*:*:*"
    ]
  }
}

data "aws_vpc" "vpc" {
  filter {
    name   = "tag:Name"
    values = [var.vpc_name]
  }
}

data "aws_subnets" "private-subnets" {
  filter {
    name   = "tag:Name"
    values = ["${var.vpc_name}-private-*"]
  }
}
