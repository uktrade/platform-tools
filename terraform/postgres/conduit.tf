data "aws_region" "current" {}

resource "aws_ecs_task_definition" "conduit_postgres" {
  # checkov:skip=CKV_AWS_336:Cannot set 'readonlyRootFilesystem = true' as it breaks ecs exec command used by conduits
  for_each = local.conduit_task_definitions

  family = "conduit-postgres-${each.key}-${local.name}"
  container_definitions = jsonencode([
    merge({
      name      = "conduit-postgres-${each.key}-${local.name}"
      image     = "public.ecr.aws/uktrade/tunnel:postgres"
      essential = true
      runtimePlatform = {
        cpuArchitecture       = "ARM64"
        operatingSystemFamily = "LINUX"
      }
      linuxParameters = {
        initProcessEnabled = true
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.conduit-logs.name
          awslogs-region        = data.aws_region.current.region
          mode                  = "non-blocking"
          awslogs-create-group  = "true"
          max-buffer-size       = "25m"
          awslogs-stream-prefix = "conduit/postgres-${each.key}"
        }
      }
    }, each.value)
  ])

  cpu                      = 512
  memory                   = 1024
  requires_compatibilities = ["FARGATE"]
  task_role_arn            = aws_iam_role.conduit-task-role.arn
  execution_role_arn       = aws_iam_role.conduit-execution-role.arn
  network_mode             = "awsvpc"
  runtime_platform {
    cpu_architecture        = "ARM64"
    operating_system_family = "LINUX"
  }
}

resource "aws_iam_role" "conduit-task-role" {
  name               = "${local.name}-conduit-task-role"
  assume_role_policy = data.aws_iam_policy_document.assume_ecstask_role.json
  tags               = local.tags
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
      "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:/conduit/postgres/${var.name}/${var.environment}/${var.name}:*",
      "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:/conduit/postgres/${var.name}/${var.environment}/${var.name}:log-stream:*"
    ]
  }

  # Needs 'resources = ["*"]' permission because the SSM agent running inside the conduit ECS task communicates with Amazon Message Gateway Service via ssmmessages actions.
  # See https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonmessagegatewayservice.html#amazonmessagegatewayservice-resources-for-iam-policies
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
  name               = "${local.name}-conduit-exec-role"
  assume_role_policy = data.aws_iam_policy_document.assume_ecstask_role.json
  tags               = local.tags
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
      "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:/conduit/postgres/${var.name}/${var.environment}/${var.name}:*",
      "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:/conduit/postgres/${var.name}/${var.environment}/${var.name}:log-stream:*"
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
      "arn:aws:ssm:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:parameter/copilot/${var.application}/${var.environment}/secrets/${local.application_user_secret_name}",
      "arn:aws:ssm:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:parameter/copilot/${var.application}/${var.environment}/secrets/${local.read_only_secret_name}"
    ]
  }

  statement {
    actions = [
      "secretsmanager:GetSecretValue"
    ]
    effect = "Allow"
    resources = [
      aws_db_instance.default.master_user_secret[0].secret_arn
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
      "arn:aws:ssm:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:parameter/copilot/${var.application}/${var.environment}/secrets/${local.application_user_secret_name}",
      "arn:aws:ssm:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:parameter/copilot/${var.application}/${var.environment}/secrets/${local.read_only_secret_name}"
    ]
  }
}

resource "aws_kms_key" "conduit-log-group-kms-key" {
  description         = "KMS Key for ${var.name}-${var.environment} conduit postgres log encryption"
  enable_key_rotation = true
  tags                = local.tags
}

resource "aws_cloudwatch_log_group" "conduit-logs" {
  # checkov:skip=CKV_AWS_338:Retains logs for 7 days instead of 1 year
  name              = "/conduit/postgres/${var.name}/${var.environment}/${var.name}"
  retention_in_days = 7
  tags              = local.tags
  kms_key_id        = aws_kms_key.conduit-log-group-kms-key.arn

  depends_on = [aws_kms_key.conduit-log-group-kms-key]
}

resource "aws_cloudwatch_log_subscription_filter" "conduit-logs-filter" {
  name            = "/conduit/postgres/${var.application}/${var.environment}/${var.name}"
  role_arn        = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"
  log_group_name  = aws_cloudwatch_log_group.conduit-logs.name
  filter_pattern  = ""
  destination_arn = local.central_log_group_destination
}

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
          "Service" : "logs.${data.aws_region.current.region}.amazonaws.com"
        },
        "Action" : "kms:*",
        "Resource" : "*"
      }
    ]
    Version = "2012-10-17"
  })
}
