data "aws_vpc" "vpc" {
  #depends_on = [module.platform-vpc]
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

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}


resource "aws_elasticache_replication_group" "redis" {
  # checkov:skip=CKV_AWS_31:Potential cascading impact on Celery. Requires further analysis - DBTP-1216
  # checkov:skip=CKV_AWS_191:Potential cascading impact on Celery. Requires further analysis - DBTP-1216
  replication_group_id       = "${var.name}-${var.environment}"
  description                = "${var.name}-${var.environment}-redis-cluster"
  engine                     = "redis"
  engine_version             = var.config.engine
  node_type                  = coalesce(var.config.instance, "cache.t4g.micro")
  num_node_groups            = 1
  replicas_per_node_group    = coalesce(var.config.replicas, 1)
  parameter_group_name       = "default.${local.redis_engine_version_map[var.config.engine]}"
  port                       = 6379
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  apply_immediately          = coalesce(var.config.apply_immediately, false)
  automatic_failover_enabled = coalesce(var.config.automatic_failover_enabled, false)
  multi_az_enabled           = coalesce(var.config.multi_az_enabled, false)
  subnet_group_name          = aws_elasticache_subnet_group.es-subnet-group.name
  security_group_ids         = [aws_security_group.redis.id]

  log_delivery_configuration {
    log_type         = "slow-log"
    destination      = aws_cloudwatch_log_group.redis-slow-log-group.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
  }

  log_delivery_configuration {
    log_type         = "engine-log"
    destination      = aws_cloudwatch_log_group.redis-engine-log-group.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
  }

  tags = local.tags
}

resource "aws_security_group" "redis" {
  name        = "${var.name}-${var.environment}-redis-security-group"
  vpc_id      = data.aws_vpc.vpc.id
  description = "Allow ingress from VPC for Redis"

  ingress {
    description = "Allow from VPC on port 6379"
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.vpc.cidr_block]
  }
  egress {
    description = "Allow all traffic"
    from_port   = 0
    to_port     = 0
    protocol    = -1
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = local.tags
}

resource "aws_kms_key" "ssm_redis_endpoint" {
  # checkov:skip=CKV2_AWS_64:skipping pending discussion with rest of team on the policy
  description             = "KMS key for ${var.name}-${var.application}-${var.environment}-redis-cluster SSM parameters"
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
      aws_kms_key.ssm_redis_endpoint.arn,
      aws_ssm_parameter.redis_url.arn,
      aws_ssm_parameter.endpoint.arn,
      aws_ssm_parameter.endpoint_short.arn,
      "arn:aws:logs:*:*:*"
    ]
  }
}

resource "aws_ssm_parameter" "endpoint_short" {
  name        = "/copilot/${var.application}/${var.environment}/secrets/${upper(replace(var.name, "-", "_"))}"
  description = "Redis endpoint (Deprecated in favour of endpoint_ssl which has the ssl_cert_reqs parameter baked in)"
  type        = "SecureString"
  value       = "rediss://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379"

  tags = local.tags

  key_id = aws_kms_key.ssm_redis_endpoint.arn
}

resource "aws_ssm_parameter" "endpoint" {
  name        = "/copilot/${var.application}/${var.environment}/secrets/${upper(replace("${var.name}_ENDPOINT", "-", "_"))}"
  description = "Redis endpoint (Deprecated in favour of endpoint_ssl which has the ssl_cert_reqs parameter baked in)"
  type        = "SecureString"
  value       = "rediss://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379"

  tags = local.tags

  key_id = aws_kms_key.ssm_redis_endpoint.arn
}

resource "aws_ssm_parameter" "redis_url" {
  name        = "/copilot/${var.application}/${var.environment}/secrets/${upper(replace("${var.name}_URL", "-", "_"))}"
  description = "Redis endpoint with SSL configuration"
  type        = "SecureString"
  value       = "rediss://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379?ssl_cert_reqs=CERT_REQUIRED"

  tags = local.tags

  key_id = aws_kms_key.ssm_redis_endpoint.arn
}

resource "aws_elasticache_subnet_group" "es-subnet-group" {
  name       = "${var.name}-${var.environment}-cache-subnet"
  subnet_ids = tolist(data.aws_subnets.private-subnets.ids)

  tags = merge(
    local.tags,
    {
      copilot-vpc = var.vpc_name
    }
  )
}

resource "aws_kms_key" "redis-log-group-kms-key" {
  description         = "KMS Key for ${var.name}-${var.environment} Redis Log encryption"
  enable_key_rotation = true
  tags                = local.tags
}

resource "aws_kms_key_policy" "redis-to-cloudwatch" {
  key_id = aws_kms_key.redis-log-group-kms-key.key_id
  policy = jsonencode({
    Id = "RedisToCloudWatch"
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
          "Service" : "logs.${data.aws_region.current.id}.amazonaws.com"
        },
        "Action" : "kms:*",
        "Resource" : "*"
      }
    ]
    Version = "2012-10-17"
  })
}
resource "aws_cloudwatch_log_group" "redis-slow-log-group" {
  # checkov:skip=CKV_AWS_338:Retains logs for 7 days instead of 1 year
  name              = "/aws/elasticache/${var.name}/${var.environment}/${var.name}Redis/slow"
  retention_in_days = 7
  tags              = local.tags
  kms_key_id        = aws_kms_key.redis-log-group-kms-key.arn
}

resource "aws_cloudwatch_log_group" "redis-engine-log-group" {
  # checkov:skip=CKV_AWS_338:Retains logs for 7 days instead of 1 year
  name              = "/aws/elasticache/${var.name}/${var.environment}/${var.name}Redis/engine"
  retention_in_days = 7
  tags              = local.tags
  kms_key_id        = aws_kms_key.redis-log-group-kms-key.arn
}

data "aws_ssm_parameter" "log-destination-arn" {
  name = "/copilot/tools/central_log_groups"
}

resource "aws_cloudwatch_log_subscription_filter" "redis-subscription-filter-engine" {
  name            = "/aws/elasticache/${var.application}/${var.environment}/${var.name}/engine"
  role_arn        = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"
  log_group_name  = aws_cloudwatch_log_group.redis-engine-log-group.name
  filter_pattern  = ""
  destination_arn = local.central_log_group_destination
}

resource "aws_cloudwatch_log_subscription_filter" "redis-subscription-filter-slow" {
  name            = "/aws/elasticache/${var.application}/${var.environment}/${var.name}/slow"
  role_arn        = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"
  log_group_name  = aws_cloudwatch_log_group.redis-slow-log-group.name
  filter_pattern  = ""
  destination_arn = local.central_log_group_destination
}
