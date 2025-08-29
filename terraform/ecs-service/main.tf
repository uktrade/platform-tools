resource "aws_ecs_task_definition" "default_nginx_task_def" {
  family                   = "${local.full_service_name}-default-task-def"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  network_mode             = "awsvpc"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn #TODO - Create separate role?
  task_role_arn            = aws_iam_role.ecs_task_role.arn           #TODO - Create separate role?
  tags                     = local.tags

  runtime_platform {
    cpu_architecture        = "ARM64"
    operating_system_family = "LINUX"
  }

  container_definitions = jsonencode([
    {
      name      = "nginx"
      image     = "public.ecr.aws/nginx/nginx:alpine-slim"
      essential = true
      portMappings = [
        {
          containerPort = 8080
          hostPort      = 8080
        }
      ]
      logConfiguration = {
        logDriver = "awslogs",
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs_service_logs.name
          awslogs-region        = data.aws_region.current.region
          mode                  = "non-blocking"
          awslogs-create-group  = "true"
          max-buffer-size       = "25m"
          awslogs-stream-prefix = "platform/ecs"
        }
      }
      runtimePlatform = {
        cpuArchitecture       = "ARM64",
        operatingSystemFamily = "LINUX"
      }
    }
  ])
}

data "aws_ecs_cluster" "cluster" {
  cluster_name = "${var.application}-${var.environment}-cluster"
}

data "aws_security_group" "env_security_group" {
  name = "${var.application}-${var.environment}-environment"
}

data "aws_subnets" "private-subnets" {
  filter {
    name   = "tag:Name"
    values = ["${local.vpc_name}-private-*"]
  }
}

resource "aws_ecs_service" "service" {
  name            = "${var.application}-${var.environment}-${var.service_config.name}"
  cluster         = data.aws_ecs_cluster.cluster.id
  launch_type     = "FARGATE"
  task_definition = aws_ecs_task_definition.default_nginx_task_def.arn
  desired_count   = 1

  # TODO - Add back in once listener rule is created
  # dynamic "load_balancer" {
  #   for_each = local.web_service_required == 1 ? [""] : []
  #   content {
  #     target_group_arn = aws_lb_target_group.target_group[0].arn
  #     container_name   = "nginx"
  #     container_port   = 8080
  #   }
  # }

  network_configuration {
    subnets         = data.aws_subnets.private-subnets.ids
    security_groups = [data.aws_security_group.env_security_group.id]
  }

  service_registries {
    registry_arn   = aws_service_discovery_service.service_discovery_service[0].arn
    container_name = "nginx"
    container_port = 443
  }

  lifecycle {
    ignore_changes = [task_definition, desired_count, service_registries]
  }

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
  description         = "KMS Key for ECS service '${local.full_service_name}' log encryption"
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
  name              = "/platform/ecs/service/${var.application}/${var.environment}/${var.service_config.name}"
  retention_in_days = 30
  tags              = local.tags
  kms_key_id        = aws_kms_key.ecs_service_log_group_kms_key.arn

  depends_on = [aws_kms_key.ecs_service_log_group_kms_key]
}

data "aws_ssm_parameter" "log-destination-arn" {
  name = "/copilot/tools/central_log_groups"
}

resource "aws_cloudwatch_log_subscription_filter" "ecs_service_logs_filter" {
  name            = "/platform/ecs/service/${var.application}/${var.environment}/${var.service_config.name}"
  role_arn        = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"
  log_group_name  = aws_cloudwatch_log_group.ecs_service_logs.name
  filter_pattern  = ""
  destination_arn = local.central_log_group_destination
}
