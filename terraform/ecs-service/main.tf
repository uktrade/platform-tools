resource "aws_ecs_task_definition" "this" {
  family                   = "${var.application}-${var.service_config.name}-${var.environment}-task-def"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.service_config.cpu)
  memory                   = tostring(var.service_config.memory)
  network_mode             = "awsvpc"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

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
            for k, v in var.service_config.variables : {
              name  = k
              value = tostring(v)
            }
          ]
          secrets = [
            for k, v in var.service_config.secrets : {
              name      = k
              valueFrom = v
            }
          ]
          logConfiguration = {
            logDriver = "awslogs"
            options = {
              awslogs-group         = "/copilot/${var.service_config.name}"
              awslogs-region        = data.aws_region.current.name
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
  filter {
    name   = "tag:Name"
    values = [local.vpc_name]
  }
}

resource "random_string" "tg_suffix" {
  length    = 6
  min_lower = 6
  special   = false
  lower     = true
}

resource "aws_lb_target_group" "target_group" {
  name                 = "${local.service_name}-tg-${random_string.tg_suffix.result}"
  port                 = 443
  protocol             = "HTTPS"
  target_type          = "ip"
  vpc_id               = data.aws_vpc.vpc.id
  deregistration_delay = 60
  tags                 = local.tags

  health_check {
    port                = try(var.service_config.http.healthcheck.port, 8080)
    path                = try(var.service_config.http.healthcheck.path, "/")
    protocol            = "HTTP"
    matcher             = try(var.service_config.http.healthcheck.success_codes, "200")
    healthy_threshold   = try(var.service_config.http.healthcheck.healthy_threshold, 3)
    unhealthy_threshold = try(var.service_config.http.healthcheck.unhealthy_threshold, 3)
    interval            = tonumber(trim(try(var.service_config.http.healthcheck.interval, "35s"), "s"))
    timeout             = tonumber(trim(try(var.service_config.http.healthcheck.timeout, "30s"), "s"))
  }
}

data "aws_service_discovery_dns_namespace" "private_dns_namespace" {
  name = "${var.environment}.${var.application}.services.local"
  type = "DNS_PRIVATE"
}

resource "aws_service_discovery_service" "service_discovery_service" {
  name = local.service_name

  dns_config {
    namespace_id = data.aws_service_discovery_dns_namespace.private_dns_namespace.id

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
