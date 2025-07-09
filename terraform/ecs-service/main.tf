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
