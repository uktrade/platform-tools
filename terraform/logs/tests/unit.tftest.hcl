mock_provider "aws" {}

variables {
  name_prefix = "test-name"
}

override_data {
  target = data.aws_iam_policy_document.log-resource-policy
  values = {
    json = "{\"Sid\": \"StateMachineToCloudWatchLogs\"}"
  }
}

run "log_resource_policy_unit_test" {
  command = plan

  assert {
    condition     = aws_cloudwatch_log_resource_policy.log-resource-policy.policy_document == "{\"Sid\": \"StateMachineToCloudWatchLogs\"}"
    error_message = "Should be: {\"Sid\": \"StateMachineToCloudWatchLogs\"}"
  }

  assert {
    condition = [
      for el in data.aws_iam_policy_document.log-resource-policy.statement[0].condition :
      true if el.variable == "aws:SourceArn"
    ][0] == true
    error_message = "Should be: aws:SourceArn"
  }

  assert {
    condition = [
      for el in data.aws_iam_policy_document.log-resource-policy.statement[0].condition :
      true if el.variable == "aws:SourceAccount"
    ][0] == true
    error_message = "Should be: aws:SourceAccount"
  }

  assert {
    condition = [
      for el in data.aws_iam_policy_document.log-resource-policy.statement[0].principals :
      true if el.type == "Service" && [
        for identifier in el.identifiers : true if identifier == "delivery.logs.amazonaws.com"
      ][0] == true
    ][0] == true
    error_message = "Should be: Service delivery.logs.amazonaws.com"
  }

  assert {
    condition = [
      for el in data.aws_iam_policy_document.log-resource-policy.statement[0].resources :
      true if strcontains(el, "log-group:/copilot/*:log-stream:*")
    ][0] == true
    error_message = "Should contain: log-group:/copilot/*:log-stream:*"
  }

  assert {
    condition = [
      for el in data.aws_iam_policy_document.log-resource-policy.statement[1].condition :
      true if el.variable == "aws:SourceArn"
    ][0] == true
    error_message = "Should be: aws:SourceArn"
  }

  assert {
    condition = [
      for el in data.aws_iam_policy_document.log-resource-policy.statement[1].condition :
      true if el.variable == "aws:SourceAccount"
    ][0] == true
    error_message = "Should be: aws:SourceAccount"
  }

  assert {
    condition = [
      for el in data.aws_iam_policy_document.log-resource-policy.statement[1].principals :
      true if el.type == "Service" && [
        for identifier in el.identifiers : true if identifier == "delivery.logs.amazonaws.com"
      ][0] == true
    ][0] == true
    error_message = "Should be: Service delivery.logs.amazonaws.com"
  }

  assert {
    condition = [
      for el in data.aws_iam_policy_document.log-resource-policy.statement[1].resources :
      true if strcontains(el, "log-group:/aws/elasticache/*")
    ][0] == true
    error_message = "Should contain log-group:/aws/elasticache/*"
  }

  assert {
    condition = [
      for el in data.aws_iam_policy_document.log-resource-policy.statement[2].condition :
      true if el.variable == "aws:SourceAccount"
    ][0] == true
    error_message = "Should be: aws:SourceAccount"
  }

  assert {
    condition = [
      for el in data.aws_iam_policy_document.log-resource-policy.statement[2].principals :
      true if el.type == "Service" && [
        for identifier in el.identifiers : true if identifier == "es.amazonaws.com"
      ][0] == true
    ][0] == true
    error_message = "Should be: Service es.amazonaws.com"
  }

  assert {
    condition = [
      for el in data.aws_iam_policy_document.log-resource-policy.statement[2].resources :
      true if strcontains(el, "log-group:/aws/opensearch/*")
    ][0] == true
    error_message = "Should contain log-group:/aws/opensearch/*"
  }
}
