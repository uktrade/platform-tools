data "aws_caller_identity" "current" {}

data "aws_ssm_parameter" "log-destination-arn" {
  name = "/copilot/tools/central_log_groups"
}

resource "aws_cloudwatch_log_subscription_filter" "rds" {
  name            = "/aws/rds/instance/${var.application}/${var.environment}/${var.name}/postgresql"
  role_arn        = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"
  log_group_name  = "/aws/rds/instance/${local.name}/postgresql"
  filter_pattern  = ""
  destination_arn = local.central_log_group_destination

  depends_on = [aws_db_instance.default]
}
