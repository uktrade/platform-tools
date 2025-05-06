resource "aws_ecs_task_definition" "conduit-redis" {
  family = "conduit-redis-read-${var.application}-${var.environment}-${var.name}"
  container_definitions = jsonencode([
    {
      name      = "conduit-redis-read-${var.application}-${var.environment}-${var.name}"
      image     = "public.ecr.aws/uktrade/tunnel:redis"
      essential = true
      secrets= [
          {
            "name": "CONNECTION_SECRET",
            "valueFrom": aws_ssm_parameter.endpoint.arn
        }
      ]
      runtimePlatform = {
        cpuArchitecture = "ARM64",
        operatingSystemFamily = "LINUX"
      },
      linuxParameters = {
        initProcessEnabled = true
      }
      logConfiguration = {
        logDriver = "awslogs",
        options = {
          awslogs-group         = aws_cloudwatch_log_group.conduit-logs.name
          awslogs-region        = data.aws_region.current.name
          mode                  = "non-blocking"
          awslogs-create-group  = "true"
          max-buffer-size       = "25m"
          awslogs-stream-prefix = "conduit/redis"
        }
      }
    }
  ])

  cpu    = 512
  memory = 1024

  requires_compatibilities = ["FARGATE"]

  task_role_arn      = aws_iam_role.conduit-task-role.arn
  execution_role_arn = aws_iam_role.conduit-execution-role.arn
  network_mode       = "awsvpc"

  runtime_platform {
    cpu_architecture        = "ARM64"
    operating_system_family = "LINUX"
  }
}

resource "aws_iam_role" "conduit-task-role" {
  name = "${var.application}-${var.environment}-${var.name}-conduit-task-role"
  assume_role_policy = data.aws_iam_policy_document.assume_ecstask_role.json #TODO - Re-using existing resource
  tags = local.tags
}

resource "aws_iam_role_policy" "access_for_conduit_ecs_task" {
  name   = "AllowConduitTaskAccess"
  role   = aws_iam_role.conduit-task-role.name
  policy = data.aws_iam_policy_document.conduit_task_role_access.json
}

data "aws_iam_policy_document" "conduit_task_role_access" {
  statement {
    actions = [
      "logs:CreateLogStream",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams",
      "logs:PutLogEvents"
    ]
    effect = "Allow"
    resources = [
      "arn:aws:logs:*:*:*"
    ]
  }

  statement {
    actions = [
      "ssmmessages:CreateControlChannel",
      "ssmmessages:OpenControlChannel",
      "ssmmessages:CreateDataChannel",
      "ssmmessages:OpenDataChannel"
    ]
    effect = "Allow"
    resources = [
      "*"
    ]
  }
}

resource "aws_iam_role" "conduit-execution-role" {
  name = "${var.application}-${var.environment}-${var.name}-conduit-execution-role"
  assume_role_policy = data.aws_iam_policy_document.assume_ecstask_role.json
  tags = local.tags
}

resource "aws_iam_role_policy" "conduit-execution-policy" {
  name   = "AllowConduitLogsAccess"
  role   = aws_iam_role.conduit-execution-role.name
  policy = data.aws_iam_policy_document.conduit_exec_policy.json
}

data "aws_iam_policy_document" "conduit_exec_policy" {
  statement {
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    effect = "Allow"
    resources = [
      "arn:aws:logs:*:*:*"
    ]
  }

  statement {
    actions = [
      "ssm:Describe*",
      "ssm:Get*",
      "ssm:List*"
    ]
    effect = "Allow"
    resources = [
      "*"
    ]
  }

  statement {
    actions = [
      "ssm:GetParameters",
      "logs:CreateLogStream",
      "kms:Decrypt"
    ]
    effect = "Allow"
    resources = [
      aws_ssm_parameter.endpoint.arn,
      aws_kms_key.ssm_redis_endpoint.arn
    ]
  }
}

# resource "aws_kms_key" "conduit-log-group-kms-key" {
#   description         = "KMS Key for ${var.name}-${var.environment} conduit redis log encryption"
#   enable_key_rotation = true
#   tags                = local.tags
# }

resource "aws_cloudwatch_log_group" "conduit-logs" {
  name              = "/conduit/redis/${var.name}/${var.environment}/${var.name}"
  retention_in_days = 7
  tags              = local.tags
  kms_key_id        = aws_kms_key.redis-log-group-kms-key.arn

}

resource "aws_cloudwatch_log_subscription_filter" "conduit-logs-filter" {
  name            = "/conduit/redis/${var.application}/${var.environment}/${var.name}"
  role_arn        = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"
  log_group_name  = aws_cloudwatch_log_group.conduit-logs.name
  filter_pattern  = ""
  destination_arn = local.central_log_group_destination
}

# resource "aws_kms_key_policy" "conduit-to-cloudwatch" {
#   key_id = aws_kms_key.conduit-log-group-kms-key.key_id
#   policy = jsonencode({
#     Id = "ConduitToCloudWatch"
#     Statement = [
#       {
#         "Sid" : "Enable IAM User Permissions",
#         "Effect" : "Allow",
#         "Principal" : {
#           "AWS" : "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
#         },
#         "Action" : "kms:*",
#         "Resource" : "*"
#       },
#       {
#         "Effect" : "Allow",
#         "Principal" : {
#           "Service" : "logs.${data.aws_region.current.name}.amazonaws.com"
#         },
#         "Action" : "kms:*",
#         "Resource" : "*"
#       }
#     ]
#     Version = "2012-10-17"
#   })
# }