# reuse rds-endpoint for sm
data "aws_security_group" "rds-endpoint" {
  name = "${var.vpc_name}-rds-endpoint-sg"
}

data "aws_iam_policy_document" "lambda-assume-role-policy" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "lambda-execution-policy" {
  # checkov:skip=CKV_AWS_108:Permissions required to perform Lambda role
  # checkov:skip=CKV_AWS_111:Permissions required to perform Lambda role
  # checkov:skip=CKV_AWS_356:Permissions required to perform Lambda role
  statement {
    effect = "Allow"
    actions = [
      # ec2 permissions required for creating a lambda within the VPC
      "ec2:CreateNetworkInterface",
      "ec2:DescribeNetworkInterfaces",
      "ec2:DeleteNetworkInterface",
      "secretsmanager:GetRandomPassword",
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "ssm:DeleteParameter",
      "ssm:PutParameter",
      "ssm:AddTagsToResource",
    ]
    resources = [
      "arn:aws:ssm:eu-west-2:*:parameter/platform/${var.application}/${var.environment}/secrets/*_OPENSEARCH_ENDPOINT"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["arn:aws:logs:*:*:*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "ssm:GetParameter",
      "kms:Decrypt",
    ]
    resources = [
      aws_ssm_parameter.opensearch_endpoint.arn,
      aws_kms_key.ssm_opensearch_endpoint.arn
    ]

  }
}

resource "aws_iam_role" "lambda-execution-role" {
  name               = "${var.application}-${var.environment}-${local.name}-lambda-role"
  path               = "/"
  assume_role_policy = data.aws_iam_policy_document.lambda-assume-role-policy.json
}

resource "aws_iam_role_policy" "lambda-execution-role-policy" {
  name   = "${var.application}-${var.environment}-${local.name}-execution-policy"
  role   = aws_iam_role.lambda-execution-role.name
  policy = data.aws_iam_policy_document.lambda-execution-policy.json
}

data "archive_file" "lambda" {
  type        = "zip"
  source_file = "${path.module}/manage_users.py"
  output_path = "${path.module}/manage_users.zip"
  depends_on = [
    aws_iam_role.lambda-execution-role
  ]
}

resource "random_string" "lambda_suffix" {
  length    = 6
  min_lower = 6
  special   = false
  lower     = true
}


resource "aws_lambda_function" "lambda" {
  # checkov:skip=CKV_AWS_272:Code signing is not currently in use
  # checkov:skip=CKV_AWS_116:Dead letter queue not required due to the nature of this function
  # checkov:skip=CKV_AWS_50:X-ray not used on platform
  filename                       = data.archive_file.lambda.output_path
  function_name                  = substr("${var.application}-${var.environment}-opensearch-create-users-${random_string.lambda_suffix.result}", 0, 64)
  role                           = aws_iam_role.lambda-execution-role.arn
  handler                        = "manage_users.handler"
  runtime                        = "python3.12"
  memory_size                    = 128
  timeout                        = 30
  reserved_concurrent_executions = -1

  source_code_hash = data.archive_file.lambda.output_base64sha256

  vpc_config {
    security_group_ids = [aws_security_group.opensearch-security-group.id, data.aws_security_group.rds-endpoint.id]
    subnet_ids         = data.aws_subnets.private-subnets.ids
  }

  tags = merge(
    local.tags,
    {
      name = local.name
    }
  )

  depends_on = [
    # When creating a Lambda function, AWS validates that the execution role
    # has fundamental permissions like ec2:CreateNetworkInterface. So we need
    # to ensure we've attached the policy to the role before trying to create
    # the lambda.
    aws_iam_role_policy.lambda-execution-role-policy,
  ]
}

resource "aws_lambda_invocation" "create-users" {
  function_name = aws_lambda_function.lambda.function_name

  input = jsonencode({
    AdminUserEndpointParam = local.ssm_parameter_name

    Application       = var.application
    Environment       = var.environment
    SecretDescription = "Opensearch endpoint secret for ${local.name}"
    ExcludeCharacters = coalesce(var.config.password_special_characters, "-_!.~$&'()*+,;=")
    Users = flatten(concat([
      {
        Username = "read",
        Index    = false,
        Read     = true,
        Write    = false
      },
      {
        Username = "write",
        Index    = false,
        Read     = true,
        Write    = true
      }
      ],
      [
        for k, v in coalesce(var.config.external_user_access, {}) :
        {
          Username = k,
          Index    = v.index,
          Read     = v.read,
          Write    = v.write
        }
      ]
    ))
  })

  depends_on = [
    aws_opensearch_domain.this,
  ]
}
