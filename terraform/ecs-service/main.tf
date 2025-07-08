resource "aws_ecs_task_definition" "aws-ecs-task" {
  family = "${local.cluster_name}-${var.service}-tf"
  container_definitions = jsonencode([
    module.web_container.json_map_object,
    module.ipfilter_container.json_map_object,
    module.appconfig_container.json_map_object,
    module.nginx_container.json_map_object
  ])

  cpu                      = 1024
  memory                   = 2048
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]

  execution_role_arn = aws_iam_role.ecsTaskExecutionRole.arn
  task_role_arn      = aws_iam_role.ecsTaskRole.arn

  # runtime_platform {
  #   operating_system_family = "LINUX"
  #   cpu_architecture = "X86_64"
  # }

  volume {
    name = "temporary-fs"
  }
  tags = local.tags
}

data "aws_ecs_task_definition" "aws-ecs-task" {
  task_definition = aws_ecs_task_definition.aws-ecs-task.family
}

resource "aws_lb_listener_rule" "https" {
  listener_arn = "arn:aws:elasticloadbalancing:eu-west-2:${data.aws_caller_identity.current.account_id}:listener/app/${var.application}-${var.environment}/6140ba7f0d63db5a/1169cc985ee8a526"
  priority     = 100
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.target_group.arn
  }

  condition {
    path_pattern {
      values = ["/*"]
    }
  }

  condition {
    host_header {
      values = ["web.${var.environment}.${var.application}.uktrade.digital"]
    }
  }
}

resource "aws_ecs_service" "aws-ecs-service" {
  name                               = "${local.cluster_name}-${var.service}-service-tf"
  cluster                            = local.cluster_name
  task_definition                    = "${aws_ecs_task_definition.aws-ecs-task.family}:${max(aws_ecs_task_definition.aws-ecs-task.revision, data.aws_ecs_task_definition.aws-ecs-task.revision)}"
  desired_count                      = 1
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  force_new_deployment               = true
  enable_execute_command             = true
  propagate_tags                     = "SERVICE"
  platform_version                   = "LATEST"

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  launch_type = "FARGATE"

  network_configuration {
    subnets = ["subnet-010f266b2fab6e77e", "subnet-0fc54a4887479d2fc"]
    security_groups = ["sg-057ada7d5600e9a5b" # Env sg
    ]

    assign_public_ip = false
  }

  service_connect_configuration {
    enabled   = true
    namespace = "${var.environment}.${var.application}.local-tf2"
    log_configuration {
      log_driver = "awslogs"
      options = {
        "awslogs-group"         = "/copilot/demodjango/${var.environment}/web",
        "awslogs-region"        = "eu-west-2",
        "awslogs-stream-prefix" = "copilot"
      }
    }
    service {
      port_name      = "target"
      discovery_name = "web-sc"
      client_alias {
        port     = 443
        dns_name = "web"
      }
    }
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.target_group.arn
    container_name   = "nginx"
    container_port   = 443
  }

  service_registries {
    registry_arn = var.service_discovery_service_arn
    port         = 443
  }
}
