resource "aws_ecs_task_definition" "this" {
  family                   = "${local.service_name}-task-def"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.service_config.cpu)
  memory                   = tostring(var.service_config.memory)
  network_mode             = "awsvpc"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  tags                     = local.tags

  container_definitions = jsonencode(
    concat(
      [
        {
          name  = var.service_config.name
          image = var.service_config.image.location
          portMappings = var.service_config.image.port != null ? [
            {
              containerPort = var.service_config.image.port
              protocol      = "tcp"
            }
          ] : []
          essential = true
          environment = [
            for k, v in coalesce(var.service_config.variables, {}) : {
              name  = k
              value = tostring(v)
            }
          ]
          secrets = [
            for k, v in coalesce(var.service_config.secrets, {}) : {
              name      = k
              valueFrom = v
            }
          ]
          logConfiguration = {
            logDriver = "awslogs"
            options = {
              awslogs-group         = "/platform/${local.service_name}/ecs-service-logs"
              awslogs-region        = data.aws_region.current.region
              awslogs-stream-prefix = "ecs"
            }
          }
        }
      ],
      [
        for sidecar_name, sidecar in var.service_config.sidecars : {
          name  = sidecar_name
          image = sidecar.image
          portMappings = sidecar.port != null ? [{
            containerPort = sidecar.port
            protocol      = "tcp"
          }] : []
          environment = sidecar.variables != null ? [
            for k, v in sidecar.variables : {
              name  = k
              value = tostring(v)
            }
          ] : []
          secrets = sidecar.secrets != null ? [
            for k, v in sidecar.secrets : {
              name      = k
              valueFrom = v
            }
          ] : []
          essential = false
        }
      ]
    )
  )
}

data "aws_vpc" "vpc" {
  count = local.web_service_required

  filter {
    name   = "tag:Name"
    values = [local.vpc_name]
  }
}

resource "random_string" "tg_suffix" {
  count = local.web_service_required

  length    = 6
  min_lower = 6
  special   = false
  lower     = true
}

resource "aws_lb_target_group" "target_group" {
  count = local.web_service_required

  name                 = "${var.service_config.name}-tg-${random_string.tg_suffix[count.index].result}"
  port                 = 443
  protocol             = "HTTPS"
  target_type          = "ip"
  vpc_id               = data.aws_vpc.vpc[count.index].id
  deregistration_delay = 60
  tags                 = local.tags

  health_check {
    port                = try(var.service_config.http.healthcheck.port, 8080)
    path                = try(var.service_config.http.healthcheck.path, "/")
    protocol            = "HTTP"
    matcher             = try(var.service_config.http.healthcheck.success_codes, "200")
    healthy_threshold   = tonumber(try(var.service_config.http.healthcheck.healthy_threshold, 3))
    unhealthy_threshold = tonumber(try(var.service_config.http.healthcheck.unhealthy_threshold, 3))
    interval            = tonumber(trim(coalesce(var.service_config.http.healthcheck.interval, "35s"), "s"))
    timeout             = tonumber(trim(coalesce(var.service_config.http.healthcheck.timeout, "30s"), "s"))
  }
}

data "aws_service_discovery_dns_namespace" "private_dns_namespace" {
  count = local.web_service_required

  name = "${var.environment}.${var.application}.services.local"
  type = "DNS_PRIVATE"
}

resource "aws_service_discovery_service" "service_discovery_service" {
  count = local.web_service_required

  name = var.service_config.name
  tags = local.tags

  dns_config {
    namespace_id = data.aws_service_discovery_dns_namespace.private_dns_namespace[count.index].id

    dns_records {
      ttl  = 10
      type = "A"
    }

    dns_records {
      ttl  = 10
      type = "SRV"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}

resource "aws_kms_key" "ecs_service_log_group_kms_key" {
  description         = "KMS Key for ECS service '${local.service_name}' log encryption"
  enable_key_rotation = true
  tags                = local.tags
}

resource "aws_kms_alias" "ecs_service_logs_kms_alias" {
  depends_on    = [aws_kms_key.ecs_service_log_group_kms_key]
  name          = "alias/${var.application}-${var.environment}-${var.service_config.name}-ecs-service-logs-key"
  target_key_id = aws_kms_key.ecs_service_log_group_kms_key.id
}

resource "aws_kms_key_policy" "ecs_service_logs_key_policy" {
  key_id = aws_kms_key.ecs_service_log_group_kms_key.key_id
  policy = jsonencode({
    Id = "EcsServiceToCloudWatch"
    Statement = [
      {
        "Sid" : "Allow Root User Permissions",
        "Effect" : "Allow",
        "Principal" : {
          "AWS" : "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        },
        "Action" : "kms:*",
        "Resource" : "*"
      },
      {
        "Sid" : "AllowCloudWatchLogsUsage"
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "logs.${data.aws_region.current.region}.amazonaws.com"
        },
        "Action" : [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        "Resource" : "*"
      }
    ]
    Version = "2012-10-17"
  })
}

resource "aws_cloudwatch_log_group" "ecs_service_logs" {
  # checkov:skip=CKV_AWS_338:Retains logs for 30 days instead of 1 year
  name              = "/platform/${local.service_name}/ecs-service-logs"
  retention_in_days = 30
  tags              = local.tags
  kms_key_id        = aws_kms_key.ecs_service_log_group_kms_key.arn

  depends_on = [aws_kms_key.ecs_service_log_group_kms_key]
}
