resource "aws_ecs_task_definition" "conduit-opensearch" {
  # checkov:skip=CKV_AWS_336:Cannot set 'readonlyRootFilesystem = true' as it breaks ecs exec command used by conduits
  family = "conduit-opensearch-read-${var.application}-${var.environment}-${var.name}"
  container_definitions = jsonencode([
    {
      name      = "conduit-opensearch-read-${var.application}-${var.environment}-${var.name}"
      image     = "public.ecr.aws/uktrade/tunnel:opensearch"
      essential = true
      secrets = [
        {
          "name" : "CONNECTION_SECRET",
          "valueFrom" : aws_ssm_parameter.opensearch_endpoint.arn
        }
      ]
      runtimePlatform = {
        cpuArchitecture       = "ARM64",
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
          awslogs-stream-prefix = "conduit/opensearch"
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

resource "aws_ssm_parameter" "opensearch_vpc_name" {
  # checkov:skip=CKV2_AWS_34: AWS SSM Parameter doesn't need to be Encrypted
  # checkov:skip=CKV_AWS_337: AWS SSM Parameter doesn't need to be Encrypted
  name  = "/conduit/${var.application}/${var.environment}/${upper(replace("${var.name}_VPC_NAME", "-", "_"))}"
  type  = "String"
  value = var.vpc_name
  tags  = local.tags

}

resource "aws_iam_role" "conduit-task-role" {
  name               = "${var.application}-${var.environment}-${var.name}-conduit-task-role"
  assume_role_policy = data.aws_iam_policy_document.assume_ecstask_role.json
  tags               = local.tags
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
      "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/conduit/opensearch/${var.name}/${var.environment}/${var.name}:*",
      "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/conduit/opensearch/${var.name}/${var.environment}/${var.name}:log-stream:*"
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
  name               = "${var.application}-${var.environment}-${var.name}-conduit-exec-role"
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
      "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/conduit/opensearch/${var.name}/${var.environment}/${var.name}:*",
      "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/conduit/opensearch/${var.name}/${var.environment}/${var.name}:log-stream:*"
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
      aws_ssm_parameter.opensearch_endpoint.arn
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
      aws_ssm_parameter.opensearch_endpoint.arn,
      aws_kms_key.ssm_opensearch_endpoint.arn
    ]
  }
}

resource "aws_cloudwatch_log_group" "conduit-logs" {
  # checkov:skip=CKV_AWS_338:Retains logs for 7 days instead of 1 year
  name              = "/conduit/opensearch/${var.name}/${var.environment}/${var.name}"
  retention_in_days = 7
  tags              = local.tags
  kms_key_id        = aws_kms_key.cloudwatch_log_group_kms_key.arn

}

resource "aws_cloudwatch_log_subscription_filter" "conduit-logs-filter" {
  name            = "/conduit/opensearch/${var.application}/${var.environment}/${var.name}"
  role_arn        = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"
  log_group_name  = aws_cloudwatch_log_group.conduit-logs.name
  filter_pattern  = ""
  destination_arn = local.central_log_group_destination
}
