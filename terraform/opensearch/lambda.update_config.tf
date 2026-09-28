data "aws_iam_policy_document" "update-config-lambda-execution-policy" {
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
    ]
    resources = ["*"]
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

resource "aws_iam_role" "update-config-lambda-execution-role" {
  name               = substr("${random_string.lambda_suffix[1].result}-${var.application}-${var.environment}-${local.name}-lambda-role", 0, 64)
  path               = "/"
  assume_role_policy = data.aws_iam_policy_document.lambda-assume-role-policy.json
}

resource "aws_iam_role_policy" "update-config-lambda-execution-role-policy" {
  name   = substr("${random_string.lambda_suffix[1].result}-${var.application}-${var.environment}-${local.name}-execution-policy", 0, 64)
  role   = aws_iam_role.update-config-lambda-execution-role.name
  policy = data.aws_iam_policy_document.update-config-lambda-execution-policy.json
}


data "archive_file" "update-config" {
  type        = "zip"
  source_file = "${path.module}/update_config/update_config.py"
  output_path = "${path.module}/update_config/update_config.zip"
  depends_on = [
    aws_iam_role.update-config-lambda-execution-role
  ]
}

resource "aws_lambda_function" "update-config" {
  # checkov:skip=CKV_AWS_272:Code signing is not currently in use
  # checkov:skip=CKV_AWS_116:Dead letter queue not required due to the nature of this function
  # checkov:skip=CKV_AWS_50:X-ray not used on platform
  filename                       = data.archive_file.update-config.output_path
  function_name                  = substr("${var.application}-${var.environment}-opensearch-update-config-${random_string.lambda_suffix[1].result}", 0, 64)
  role                           = aws_iam_role.lambda-execution-role.arn
  handler                        = "update_config.handler"
  runtime                        = "python3.14"
  memory_size                    = 128
  timeout                        = 30
  reserved_concurrent_executions = -1

  source_code_hash = data.archive_file.update-config.output_base64sha256

  vpc_config {
    security_group_ids = [aws_security_group.opensearch-security-group.id, data.aws_security_group.rds-endpoint.id]
    subnet_ids         = data.aws_subnets.private-subnets.ids
  }

  tags = merge(
    local.tags,
    {
      name   = local.name,
      lambda = "update-config"
    }
  )

  depends_on = [
    # When creating a Lambda function, AWS validates that the execution role
    # has fundamental permissions like ec2:CreateNetworkInterface. So we need
    # to ensure we've attached the policy to the role before trying to create
    # the lambda.
    aws_iam_role_policy.update-config-lambda-execution-role-policy,
  ]
}

resource "aws_lambda_invocation" "logging" {
  function_name = aws_lambda_function.update-config.function_name

  input = jsonencode({
    AdminUserEndpointParam = local.ssm_parameter_name

    Application = var.application
    Environment = var.environment
  })

  depends_on = [
    aws_opensearch_domain.this,
  ]
}