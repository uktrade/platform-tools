resource "aws_kms_key" "ecs_service_log_group_kms_key" {
  description         = "KMS Key for ECS service '${local.full_service_name}' log encryption"
  enable_key_rotation = true
  tags                = local.tags
}

resource "aws_kms_key_policy" "ecs_service_logs_key_policy" {
  key_id = aws_kms_key.ecs_service_log_group_kms_key.key_id
  policy = jsonencode({
    Id = "EcsServiceToCloudWatch"
    Statement = [
      {
        "Sid" : "Allow Root User Permissions",
        "Effect" : "Allow",
        "Principal" : {
          "AWS" : "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        },
        "Action" : "kms:*",
        "Resource" : "*"
      },
      {
        "Sid" : "AllowCloudWatchLogsUsage"
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "logs.${data.aws_region.current.region}.amazonaws.com"
        },
        "Action" : [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        "Resource" : "*"
      }
    ]
    Version = "2012-10-17"
  })
}

resource "aws_cloudwatch_log_group" "ecs_service_logs" {
  # checkov:skip=CKV_AWS_338:Retains logs for 30 days instead of 1 year
  name              = "/platform/ecs/service/${var.application}/${var.environment}/${var.service_config.name}"
  retention_in_days = 30
  tags              = local.tags
  kms_key_id        = aws_kms_key.ecs_service_log_group_kms_key.arn
  depends_on = [
    time_sleep.kms_delay
  ]
}

resource "time_sleep" "kms_delay" {
  depends_on      = [aws_kms_key.ecs_service_log_group_kms_key]
  create_duration = "10s"
}

data "aws_ssm_parameter" "log-destination-arn" {
  name = "/copilot/tools/central_log_groups"
}

resource "aws_cloudwatch_log_subscription_filter" "ecs_service_logs_filter" {
  name            = "/platform/ecs/service/${var.application}/${var.environment}/${var.service_config.name}"
  role_arn        = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"
  log_group_name  = aws_cloudwatch_log_group.ecs_service_logs.name
  filter_pattern  = ""
  destination_arn = local.central_log_group_destination
}
