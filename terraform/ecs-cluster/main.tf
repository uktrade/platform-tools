data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "aws_ecs_cluster" "cluster" {
  name = local.cluster_name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  configuration {
    execute_command_configuration {
      logging = "DEFAULT"
    }
  }

  tags = local.tags
}

resource "aws_ecs_cluster_capacity_providers" "capacity" {
  cluster_name = aws_ecs_cluster.cluster.name

  capacity_providers = ["FARGATE", "FARGATE_SPOT"]
}

resource "aws_cloudwatch_log_group" "service_logs" {
  for_each = var.services

  name = "/terraform/${var.application}/${var.environment}/${each.key}"

  retention_in_days = 30
  tags              = local.tags
}

resource "aws_cloudwatch_log_subscription_filter" "service_logs_subscription_filter" {
  for_each = var.services

  name            = "/terraform/${var.application}/${var.environment}/${each.key}"
  log_group_name  = aws_cloudwatch_log_group.service_logs[each.key].name
  filter_pattern  = ""
  destination_arn = local.log_destination_arn
  role_arn        = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"

  depends_on = [aws_cloudwatch_log_group.service_logs]
}
