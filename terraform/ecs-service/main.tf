resource "aws_ssm_parameter" "service_data" {
  # checkov:skip=CKV2_AWS_34: This AWS SSM Parameter doesn't need to be encrypted
  name = "/platform/applications/${var.application}/environments/${var.environment}/services/${var.service_config.name}"
  tier = "Intelligent-Tiering"
  type = "String"
  value = jsonencode({
    "name" : var.service_config.name,
    "type" : var.service_config.type
  })
  tags = local.tags
}

resource "aws_s3_object" "task_definition" {
  for_each     = toset(local.is_scheduled_job ? [] : ["enabled"])
  bucket       = "ecs-task-definitions-${var.application}-${var.environment}"
  key          = "${var.application}/${var.environment}/${var.service_config.name}.json"
  content      = local.task_definition_json
  content_type = "application/json"
  tags         = local.tags
}

moved {
  from = aws_s3_object.task_definition
  to   = aws_s3_object.task_definition["enabled"]
}

# Dummy task definition used for first deployment. Cannot create an ECS service without a task def.
resource "aws_ecs_task_definition" "default_task_def" {
  # checkov:skip=CKV_AWS_336: Nginx needs access to a few paths on the root filesystem
  for_each                 = toset(local.is_scheduled_job ? [] : ["enabled"])
  family                   = "${local.full_service_name}-task-def" # Same name as the actual task definition the service will have
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  network_mode             = "awsvpc"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  tags                     = local.tags
  pid_mode                 = "task"

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

moved {
  from = aws_ecs_task_definition.default_task_def
  to   = aws_ecs_task_definition.default_task_def["enabled"]
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
  triggers = {
    service_deployment_mode = local.service_deployment_mode
  }
}

resource "aws_ecs_service" "service" {
  for_each                          = toset(local.is_scheduled_job ? [] : ["enabled"])
  name                              = "${var.application}-${var.environment}-${var.service_config.name}"
  cluster                           = data.aws_ecs_cluster.cluster.id
  launch_type                       = "FARGATE"
  enable_execute_command            = var.service_config.exec
  task_definition                   = aws_ecs_task_definition.default_task_def["enabled"].arn # Dummy task definition used for first deployment. Cannot create an ECS service without a task def.
  propagate_tags                    = "SERVICE"
  desired_count                     = 1                                                         # Dummy count used only for the first deployment. For subsequent deployments, desired_count is controlled by ECS autoscaling which is always enabled.
  health_check_grace_period_seconds = try(var.service_config.http.healthcheck.grace_period, 30) # NOTE: This is problematic for Backend Services because the `var.service_config.http` block is web service specific. Long term, `grace_period` should be moved out of `http.healthcheck` into a better service-level setting so this fallback is not required.
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

  dynamic "load_balancer" {
    for_each = local.internal_service_required == 1 ? [""] : []
    content {
      target_group_arn = aws_lb_target_group.nlb_to_ecs[0].arn
      container_name   = "nginx"
      container_port   = 443
    }
  }


  # TODO - See if discovery service can be removed once de-copiloting is complete, because we already use Service Connect for the same purposes. Verify that no team uses Service Discovery before any removal.
  dynamic "service_registries" {
    for_each = local.ecs_service_connect_required == 1 ? [""] : []

    content {
      registry_arn = aws_service_discovery_service.service_discovery_service[0].arn
      port         = local.web_service_required == 1 ? 443 : try(var.service_config.image.port, 8080)
    }
  }

  dynamic "service_connect_configuration" {
    for_each = local.ecs_service_connect_required == 1 ? [""] : []

    content {
      enabled   = true
      namespace = data.aws_service_discovery_dns_namespace.private_dns_namespace[0].arn

      service {
        discovery_name = "${var.service_config.name}-sc"
        port_name      = "target"
        client_alias {
          dns_name = var.service_config.name
          port     = local.web_service_required == 1 || local.internal_service_required == 1 ? 443 : try(var.service_config.image.port, 8080)
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
    ignore_changes = [task_definition, desired_count] # See reasoning for this above
  }

  depends_on = [
    aws_lambda_invocation.dummy_listener_rule,
    aws_lb_listener.nlb
  ]
}

moved {
  from = aws_ecs_service.service
  to   = aws_ecs_service.service["enabled"]
}

data "aws_vpc" "vpc" {
  filter {
    name   = "tag:Name"
    values = [local.vpc_name]
  }
}

resource "random_string" "tg_suffix" {
  count = local.web_service_required + local.internal_service_required

  length    = 6
  min_lower = 6
  special   = false
  lower     = true
}

resource "aws_lb_target_group" "target_group" {
  count = local.web_service_required

  name                 = substr("${var.service_config.name}-tg-${random_string.tg_suffix[count.index].result}", 0, 32)
  port                 = 443
  protocol             = "HTTPS"
  target_type          = "ip"
  vpc_id               = data.aws_vpc.vpc.id
  deregistration_delay = var.service_config.http.deregistration_delay
  tags                 = local.tags

  health_check {
    port                = var.service_config.http.healthcheck.port
    path                = var.service_config.http.healthcheck.path
    protocol            = "HTTP"
    matcher             = var.service_config.http.healthcheck.success_codes
    healthy_threshold   = var.service_config.http.healthcheck.healthy_threshold
    unhealthy_threshold = var.service_config.http.healthcheck.unhealthy_threshold
    interval            = var.service_config.http.healthcheck.interval
    timeout             = var.service_config.http.healthcheck.timeout
  }

  stickiness {
    enabled         = var.service_config.http.stickiness
    type            = "lb_cookie"
    cookie_duration = 86400 # default AWS value, 1 day in seconds
  }
}

data "aws_service_discovery_dns_namespace" "private_dns_namespace" {
  count = local.ecs_service_connect_required

  name = "${var.environment}.${var.application}.services.local"
  type = "DNS_PRIVATE"
}

resource "aws_service_discovery_service" "service_discovery_service" {
  count = local.ecs_service_connect_required

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

###############
# SCHEDULED JOB
###############

resource "aws_ecs_task_definition" "scheduled_job" {
  for_each                 = toset(local.is_scheduled_job ? ["enabled"] : [])
  family                   = "${local.full_service_name}-task-def"
  requires_compatibilities = ["FARGATE"]
  pid_mode                 = "task"
  region                   = data.aws_region.current.region
  cpu                      = tostring(var.service_config.cpu)
  memory                   = tostring(var.service_config.memory)
  network_mode             = "awsvpc"

  dynamic "ephemeral_storage" {
    for_each = var.service_config.storage.ephemeral != null ? toset([var.service_config.storage.ephemeral]) : toset([])
    content {
      size_in_gib = ephemeral_storage.value
    }
  }

  execution_role_arn    = aws_iam_role.ecs_task_execution_role.arn
  container_definitions = jsonencode(local.container_definitions_list)
  task_role_arn         = aws_iam_role.ecs_task_role.arn

  dynamic "volume" {
    for_each = local.volumes
    content {
      name = volume.value["name"]
    }
  }

  runtime_platform {
    cpu_architecture = local.cpu_architecture
  }

  tags = local.tags
}

module "scheduling" {
  for_each            = toset(local.is_scheduled_job ? ["enabled"] : [])
  source              = "./scheduling"
  name                = local.full_service_name
  schedule            = var.service_config.schedule
  retries             = try(var.service_config.retries, null)
  timeout_seconds     = try(var.service_config.timeout, null)
  vpc_id              = data.aws_vpc.vpc.id
  task_definition_arn = aws_ecs_task_definition.scheduled_job["enabled"].arn
  subnet_ids          = data.aws_subnets.private-subnets.ids
  cluster_id          = data.aws_ecs_cluster.cluster.id
  tags                = local.tags
  log_group_arn       = aws_cloudwatch_log_group.ecs_service_logs.arn
}

################################
# LOAD BALANCED INTERNAL SERVICE
################################

data "aws_acm_certificate" "acm" {
  # This list should always be of length 1 due to the validation on the http alias 
  for_each = toset(local.internal_service_required == 1 ? var.service_config.http.alias : [])

  domain   = each.value
  statuses = ["ISSUED"]

  most_recent = true
}

data "aws_lb" "nlb" {
  count = local.internal_service_required

  name = "${var.application}-${var.environment}-nlb"
}

resource "aws_lb_target_group" "nlb_to_ecs" {
  count = local.internal_service_required

  name                 = substr("${var.service_config.name}-tg-${random_string.tg_suffix[count.index].result}", 0, 32)
  port                 = 443
  protocol             = "TLS"
  target_type          = "ip"
  vpc_id               = data.aws_vpc.vpc.id
  deregistration_delay = var.service_config.http.deregistration_delay
  tags                 = local.tags

  health_check {
    port                = var.service_config.http.healthcheck.port
    path                = var.service_config.http.healthcheck.path
    protocol            = "HTTP"
    matcher             = var.service_config.http.healthcheck.success_codes
    healthy_threshold   = var.service_config.http.healthcheck.healthy_threshold
    unhealthy_threshold = var.service_config.http.healthcheck.unhealthy_threshold
    interval            = var.service_config.http.healthcheck.interval
    timeout             = var.service_config.http.healthcheck.timeout
  }

}

resource "aws_lb_listener" "nlb" {
  for_each = local.internal_service_required == 1 ? {
    for idx, cert in data.aws_acm_certificate.acm : cert.domain => cert
  } : {}

  load_balancer_arn = data.aws_lb.nlb[0].arn
  protocol          = "TLS"
  port              = 443
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-Res-PQ-2025-09"
  certificate_arn   = each.value.arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.nlb_to_ecs[0].arn
  }

  tags = local.tags
}
