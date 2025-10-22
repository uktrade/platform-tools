resource "aws_s3_object" "task_definition" {
  bucket       = "ecs-task-definitions-${var.application}-${var.environment}"
  key          = "${var.application}/${var.environment}/${var.service_config.name}.json"
  content      = local.task_definition_json
  content_type = "application/json"
  tags         = local.tags
}

# Dummy task definition used for first deployment. Cannot create an ECS service without a task def.
resource "aws_ecs_task_definition" "default_task_def" {
  # checkov:skip=CKV_AWS_336: Nginx needs access to a few paths on the root filesystem
  family                   = "${local.full_service_name}-task-def" # Same name as the actual task definition the service will have
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  network_mode             = "awsvpc"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  tags                     = local.tags

  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  container_definitions = jsonencode([
    {
      name      = "nginx"
      image     = "public.ecr.aws/uktrade/copilot-bootstrap:latest"
      essential = true
      portMappings = [
        {
          containerPort = 443
          hostPort      = 443
          name          = "target"
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs",
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs_service_logs.name
          awslogs-region        = data.aws_region.current.region
          awslogs-stream-prefix = "platform"
        }
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

resource "aws_lambda_invocation" "dummy_listener_rule" {
  count           = local.web_service_required
  function_name   = "${var.application}-${var.environment}-listener-rule-organiser"
  lifecycle_scope = "CRUD"
  terraform_key   = "Lifecycle"
  input = jsonencode({
    ServiceName = var.service_config.name
    TargetGroup = aws_lb_target_group.target_group[0].arn
  })
}

resource "aws_ecs_service" "service" {
  name                              = "${var.application}-${var.environment}-${var.service_config.name}"
  cluster                           = data.aws_ecs_cluster.cluster.id
  launch_type                       = "FARGATE"
  enable_execute_command            = try(var.service_config.exec, false)
  task_definition                   = aws_ecs_task_definition.default_task_def.arn # Dummy task definition used for first deployment. Cannot create an ECS service without a task def.
  propagate_tags                    = "SERVICE"
  desired_count                     = 1 # Dummy count used for first deployment. For subsequent deployments, desired_count is controlled by autoscaling.
  health_check_grace_period_seconds = tonumber(trim(coalesce(try(var.service_config.http.healthcheck.grace_period, null), "30s"), "s"))
  tags                              = local.tags

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets         = data.aws_subnets.private-subnets.ids
    security_groups = [data.aws_security_group.env_security_group.id]
  }

  dynamic "load_balancer" {
    for_each = local.web_service_required == 1 ? [""] : []
    content {
      target_group_arn = aws_lb_target_group.target_group[0].arn
      container_name   = "nginx"
      container_port   = 443
    }
  }

  # TODO - See if discovery service can be removed once de-copiloting is complete, because we already use Service Connect for the same purposes. Verify that no team uses Service Discovery before any removal.
  dynamic "service_registries" {
    for_each = local.web_service_required == 1 ? [""] : []

    content {
      registry_arn = aws_service_discovery_service.service_discovery_service[0].arn
      port         = 443
    }
  }

  dynamic "service_connect_configuration" {
    for_each = local.web_service_required == 1 ? [""] : []

    content {
      enabled   = true
      namespace = data.aws_service_discovery_dns_namespace.private_dns_namespace[0].arn

      service {
        discovery_name = "${var.service_config.name}-sc"
        port_name      = "target"
        client_alias {
          dns_name = var.service_config.name
          port     = 443
        }
      }
      log_configuration {
        log_driver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs_service_logs.name
          awslogs-region        = data.aws_region.current.region
          awslogs-stream-prefix = "platform"
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [task_definition, desired_count, health_check_grace_period_seconds]
  }

  depends_on = [aws_lambda_invocation.dummy_listener_rule]
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
}

resource "aws_kms_key" "ecs_service_log_group_kms_key" {
  description         = "KMS Key for ECS service '${local.full_service_name}' log encryption"
  enable_key_rotation = true
  tags                = local.tags
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
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
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

resource "aws_appautoscaling_target" "ecs_autoscaling" {
  service_namespace  = "ecs"
  resource_id        = "service/${data.aws_ecs_cluster.cluster.cluster_name}/${local.full_service_name}"
  scalable_dimension = "ecs:service:DesiredCount"

  min_capacity = local.count_min
  max_capacity = local.count_max
}

resource "aws_appautoscaling_policy" "cpu_autoscaling_policy" {
  count = local.enable_cpu ? 1 : 0

  name               = "${local.full_service_name}-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.ecs_autoscaling.service_namespace
  resource_id        = aws_appautoscaling_target.ecs_autoscaling.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_autoscaling.scalable_dimension

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = local.cpu_value
    scale_in_cooldown  = local.cpu_cool_in
    scale_out_cooldown = local.cpu_cool_out
  }
}

resource "aws_appautoscaling_policy" "memory_autoscaling_policy" {
  count = local.enable_mem ? 1 : 0

  name               = "${local.full_service_name}-memory-autoscaling"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.ecs_autoscaling.service_namespace
  resource_id        = aws_appautoscaling_target.ecs_autoscaling.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_autoscaling.scalable_dimension

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value       = local.mem_value
    scale_in_cooldown  = local.mem_cool_in
    scale_out_cooldown = local.mem_cool_out
  }
}

# Look up the ALB that is attached to the TG (after the listener-rule Lambda runs)
data "aws_lb" "load_balancer" {
  count = local.enable_req ? 1 : 0
  arn   = one(aws_lb_target_group.target_group[0].load_balancer_arns)
}

# This policy is only for 'Load Balanced Web Service' type services
resource "aws_appautoscaling_policy" "requests_autoscaling_policy" {
  count = local.enable_req ? 1 : 0

  name               = "${local.full_service_name}-req-100"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.ecs_autoscaling.service_namespace
  resource_id        = aws_appautoscaling_target.ecs_autoscaling.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_autoscaling.scalable_dimension

  # Ensure the listener-rule Lambda runs first to attach the TG on the ALB
  depends_on = [aws_lambda_invocation.dummy_listener_rule]

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      # Very specific format required: app/<load-balancer-name>/<load-balancer-id>/targetgroup/<target-group-name>/<target-group-id>
      # See AWS docs: https://docs.aws.amazon.com/autoscaling/plans/APIReference/API_PredefinedScalingMetricSpecification.html
      resource_label = "${data.aws_lb.load_balancer[0].arn_suffix}/${aws_lb_target_group.target_group[0].arn_suffix}"
    }
    target_value       = local.req_value
    scale_in_cooldown  = local.req_cool_in
    scale_out_cooldown = local.req_cool_out
  }
}

resource "aws_ssm_parameter" "service_data" {
  name = "/platform/applications/${var.application}/environments/${var.environment}/services/${var.service_config.name}"
  tier = "Intelligent-Tiering"
  type = "String"
  value = jsonencode({
    "name" : var.service_config.name,
    "type" : var.service_config.type
  })
  tags = local.tags
}
