data "aws_ssm_parameter" "log-destination-arn" {
  name = "/copilot/tools/central_log_groups"
}

resource "aws_cloudwatch_log_subscription_filter" "opensearch_log_group_index_slow_logs" {
  name            = "/aws/opensearch/${var.application}/${var.environment}/${var.name}/opensearch_log_group_index_slow"
  role_arn        = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"
  log_group_name  = "/aws/opensearch/${local.domain_name}/index-slow"
  filter_pattern  = ""
  destination_arn = local.central_log_group_destination

  depends_on = [aws_cloudwatch_log_group.opensearch_log_group_index_slow_logs]
}

resource "aws_cloudwatch_log_subscription_filter" "opensearch_log_group_search_slow_logs" {
  name            = "/aws/opensearch/${var.application}/${var.environment}/${var.name}/opensearch_log_group_search_slow"
  role_arn        = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"
  log_group_name  = "/aws/opensearch/${local.domain_name}/search-slow"
  filter_pattern  = ""
  destination_arn = local.central_log_group_destination

  depends_on = [aws_cloudwatch_log_group.opensearch_log_group_search_slow_logs]
}

resource "aws_cloudwatch_log_subscription_filter" "opensearch_log_group_es_application_logs" {
  name            = "/aws/opensearch/${var.application}/${var.environment}/${var.name}/opensearch_log_group_es_application"
  role_arn        = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"
  log_group_name  = "/aws/opensearch/${local.domain_name}/es-application"
  filter_pattern  = ""
  destination_arn = local.central_log_group_destination

  depends_on = [aws_cloudwatch_log_group.opensearch_log_group_es_application_logs]
}

resource "aws_cloudwatch_log_subscription_filter" "opensearch_log_group_audit_logs" {
  name            = "/aws/opensearch/${var.application}/${var.environment}/${var.name}/opensearch_log_group_audit"
  role_arn        = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"
  log_group_name  = "/aws/opensearch/${local.domain_name}/audit"
  filter_pattern  = ""
  destination_arn = local.central_log_group_destination

  depends_on = [aws_cloudwatch_log_group.opensearch_log_group_audit_logs]
}
