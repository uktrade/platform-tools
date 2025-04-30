resource "aws_ecs_task_definition" "conduit-postgres" {
  family = "conduit-${local.name}"
  container_definitions = jsonencode([
    {
      name      = "conduit-${local.name}"
      image     = "public.ecr.aws/uktrade/tunnel:postgres" #postgres-decopilot-test
      essential = true
      environment= [
          {
            "name": "CONNECTION_SECRET",
            "value": "provided during task creation in platform-helper"
        }
      ]
      # secrets = [

      # ]

      runtimePlatform = {
        cpuArchitecture = "ARM64",
        operatingSystemFamily = "LINUX"
      },
      logConfiguration = {
        logDriver = "awslogs",
        options = {
          awslogs-group         = aws_cloudwatch_log_group.conduit-logs.name
          awslogs-region        = "eu-west-2"
          mode                  = "non-blocking"
          awslogs-create-group  = "true"
          max-buffer-size       = "25m"
          awslogs-stream-prefix = "conduit/postgres"
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
  name = "${local.name}-conduit-task-role"
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
  name   = "AllowConduitLogsAndSsmAccess"
  role   = aws_iam_role.conduit-task-role.name
  policy = data.aws_iam_policy_document.conduit_logs_ssm_access.json
}

data "aws_iam_policy_document" "conduit_logs_ssm_access" {
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
      "arn:aws:ssmmessages:*:*:*"
    ]
  }
}

resource "aws_iam_role" "conduit-execution-role" {
  name = "${local.name}-conduit-execution-role"
  assume_role_policy = data.aws_iam_policy_document.assume_ecstask_role.json
  tags = local.tags
}

resource "aws_iam_role_policy" "conduit-execution-policy" {
  name   = "AllowConduitLogsAccess"
  role   = aws_iam_role.conduit-execution-role.name
  policy = data.aws_iam_policy_document.conduit_publish_logs.json
}

data "aws_iam_policy_document" "conduit_publish_logs" {
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
}

resource "aws_kms_key" "conduit-log-group-kms-key" {
  description         = "KMS Key for ${var.name}-${var.environment} Postgres Log encryption"
  enable_key_rotation = true
  tags                = local.tags
}

resource "aws_cloudwatch_log_group" "conduit-logs" {
  name              = "/conduit/postgres/${var.name}/${var.environment}/${var.name}"
  retention_in_days = 7
  tags              = local.tags
  kms_key_id        = aws_kms_key.conduit-log-group-kms-key.arn

}

resource "aws_cloudwatch_log_subscription_filter" "conduit-logs-filter" {
  name            = "/conduit/postgres/${var.application}/${var.environment}/${var.name}"
  role_arn        = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"
  log_group_name  = aws_cloudwatch_log_group.conduit-logs.name
  filter_pattern  = ""
  destination_arn = local.central_log_group_destination
}


data "aws_region" "current" {}

resource "aws_kms_key_policy" "conduit-to-cloudwatch" {
  key_id = aws_kms_key.conduit-log-group-kms-key.key_id
  policy = jsonencode({
    Id = "ConduitToCloudWatch"
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
          "Service" : "logs.${data.aws_region.current.name}.amazonaws.com"
        },
        "Action" : "kms:*",
        "Resource" : "*"
      }
    ]
    Version = "2012-10-17"
  })
}