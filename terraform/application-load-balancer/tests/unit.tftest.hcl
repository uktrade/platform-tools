mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
      id         = "123456789012"
    user_id = "XXXXXXXXXXXXXXXXXXXXX" }
  }

}

mock_provider "aws" {
  alias = "sandbox"
}

mock_provider "aws" {
  alias = "domain"
  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
      id         = "123456789012"
    user_id = "XXXXXXXXXXXXXXXXXXXXX" }
  }
}

override_data {
  target = data.aws_vpc.vpc
  values = {
    id         = "vpc-00112233aabbccdef"
    cidr_block = "10.0.0.0/16"
  }
}
override_data {
  target = data.aws_subnets.public-subnets
  values = {
    ids = ["subnet-000111222aaabbb01"]
  }
}
override_data {
  target = data.aws_route53_zone.domain-root
  values = {
    count = 0
    name  = "dom-prefix-root.env.app.uktrade.digital"
  }
}
override_data {
  target = data.aws_route53_zone.domain-alb
  values = {
    count = 0
    name  = "dom-prefix-alb.env.app.uktrade.digital"
  }
}

override_data {
  target = data.aws_iam_policy_document.origin_verify_rotate_policy
  values = {
    json = "{\"Sid\": \"LambdaExecutionRolePolicy\"}"
  }
}


variables {
  application    = "app"
  environment    = "env"
  vpc_name       = "vpc-name"
  dns_account_id = "123456789012"
  cloudfront_id  = ["123456789"]
  config = {
    domain_prefix = "dom-prefix",
    cdn_domains_list = {
      "web.dev.my-application.uktrade.digital" : ["internal.web", "my-application.uktrade.digital"]
      "api.dev.my-application.uktrade.digital" : ["internal.api", "my-application.uktrade.digital"]
    }
    slack_alert_channel_alb_secret_rotation = "/slack/test/ssm/parameter/name"
  }
}


run "aws_lb_unit_test" {
  command = plan

  assert {
    condition     = aws_lb.this.name == "app-env"
    error_message = "Invalid name for aws_lb.this"
  }

  assert {
    condition     = aws_lb.this.load_balancer_type == "application"
    error_message = "Should be: application"
  }

  assert {
    condition     = [for el in aws_lb.this.subnets : el][0] == "subnet-000111222aaabbb01"
    error_message = "Should be: subnet-000111222aaabbb01"
  }

  assert {
    condition     = aws_lb.this.access_logs[0].bucket == "dbt-access-logs"
    error_message = "Should be: dbt-access-logs"
  }

  assert {
    condition     = aws_lb.this.access_logs[0].prefix == "app/env"
    error_message = "Should be: app/env"
  }

  assert {
    condition     = aws_lb.this.access_logs[0].enabled == true
    error_message = "Should be: true"
  }
}

run "aws_lb_listener_http_unit_test" {
  command = plan

  assert {
    condition     = aws_lb_listener.alb-listener["http"].port == 80
    error_message = "Should be: 80"
  }

  assert {
    condition     = aws_lb_listener.alb-listener["http"].protocol == "HTTP"
    error_message = "Should be: HTTP"
  }

  assert {
    condition     = aws_lb_listener.alb-listener["http"].default_action[0].type == "forward"
    error_message = "Should be: forward"
  }
}

run "aws_lb_listener_https_unit_test" {
  command = plan

  assert {
    condition     = aws_lb_listener.alb-listener["https"].port == 443
    error_message = "Should be: 443"
  }

  assert {
    condition     = aws_lb_listener.alb-listener["https"].protocol == "HTTPS"
    error_message = "Should be: HTTPS"
  }

  assert {
    condition     = aws_lb_listener.alb-listener["https"].ssl_policy == "ELBSecurityPolicy-2016-08"
    error_message = "Should be:ELBSecurityPolicy-2016-08"
  }

  assert {
    condition     = aws_lb_listener.alb-listener["https"].default_action[0].type == "forward"
    error_message = "Should be: forward"
  }
}

run "aws_security_group_http_unit_test" {
  command = plan

  assert {
    condition     = aws_security_group.alb-security-group["http"].name == "app-env-alb-http"
    error_message = "Should be: app-env-alb-http"
  }

  # Cannot test for the default on a plan
  # aws_security_group.alb-security-group["http"].revoke_rules_on_delete == false

  assert {
    condition     = aws_security_group.alb-security-group["http"].vpc_id == "vpc-00112233aabbccdef"
    error_message = "Should be: vpc-00112233aabbccdef"
  }
}

run "aws_security_group_https_unit_test" {
  command = plan

  assert {
    condition     = aws_security_group.alb-security-group["https"].name == "app-env-alb-https"
    error_message = "Should be: app-env-alb-https"
  }

  # Cannot test for the default on a plan
  # aws_security_group.alb-security-group["https"].revoke_rules_on_delete == false

  assert {
    condition     = aws_security_group.alb-security-group["https"].vpc_id == "vpc-00112233aabbccdef"
    error_message = "Should be: vpc-00112233aabbccdef"
  }
}

run "aws_lb_target_group_unit_test" {
  command = plan

  assert {
    condition     = aws_lb_target_group.http-target-group.name == "app-env-http"
    error_message = "Should be: app-env-http"
  }

  assert {
    condition     = aws_lb_target_group.http-target-group.port == 80
    error_message = "Should be: 80"
  }

  assert {
    condition     = aws_lb_target_group.http-target-group.protocol == "HTTP"
    error_message = "Should be: HTTP"
  }

  assert {
    condition     = aws_lb_target_group.http-target-group.target_type == "ip"
    error_message = "Should be: ip"
  }

  assert {
    condition     = aws_lb_target_group.http-target-group.vpc_id == "vpc-00112233aabbccdef"
    error_message = "Should be: vpc-00112233aabbccdef"
  }
}

run "aws_acm_certificate_unit_test" {
  command = plan

  assert {
    condition     = aws_acm_certificate.certificate.domain_name == "dom-prefix.env.app.uktrade.digital"
    error_message = "Should be: dom-prefix.env.app.uktrade.digital"
  }

  assert {
    condition     = length(aws_acm_certificate.certificate.subject_alternative_names) == 2
    error_message = "Should be: 2"
  }

  assert {
    condition     = [for el in aws_acm_certificate.certificate.subject_alternative_names : true if el == "web.dev.my-application.uktrade.digital"][0] == true
    error_message = "Should be: web.dev.my-application.uktrade.digital"
  }

  assert {
    condition     = [for el in aws_acm_certificate.certificate.subject_alternative_names : true if el == "api.dev.my-application.uktrade.digital"][0] == true
    error_message = "Should be: api.dev.my-application.uktrade.digital"
  }

  assert {
    condition     = aws_acm_certificate.certificate.validation_method == "DNS"
    error_message = "Should be: DNS"
  }

  assert {
    condition     = aws_acm_certificate.certificate.key_algorithm == "RSA_2048"
    error_message = "Should be: RSA_2048"
  }
}

run "aws_route53_record_unit_test" {
  command = plan

  assert {
    condition     = aws_route53_record.validation-record-san[0].ttl == 300
    error_message = "Should be: 300"
  }

  assert {
    condition     = aws_route53_record.validation-record-san[1].ttl == 300
    error_message = "Should be: 300"
  }

  assert {
    condition     = aws_route53_record.alb-record.name == "dom-prefix.env.app.uktrade.digital"
    error_message = "Should be: dom-prefix.env.app.uktrade.digital"
  }

  assert {
    condition     = aws_route53_record.alb-record.ttl == 300
    error_message = "Should be: 300"
  }

  assert {
    condition     = aws_route53_record.alb-record.type == "CNAME"
    error_message = "Should be: CNAME"
  }
}

run "domain_length_validation_tests" {
  command = plan

  variables {
    application = "app"
    environment = "env"
    config = {
      domain_prefix                           = "dom-prefix",
      cdn_domains_list                        = { "a-very-long-domain-name-used-to-test-length-validation.my-application.uktrade.digital" : ["internal", "my-application.uktrade.digital"] }
      slack_alert_channel_alb_secret_rotation = "/slack/test/ssm/parameter/name"
    }
  }

  expect_failures = [
    var.config.cdn_domains_list
  ]
}

run "domain_length_validation_tests_succeed_with_empty_cdn_domains_list_in_config" {
  command = plan

  variables {
    application = "app"
    environment = "env"
    config = {
      slack_alert_channel_alb_secret_rotation = "/slack/test/ssm/parameter/name"
    }
  }

  assert {
    condition     = var.config.cdn_domains_list == null
    error_message = "Should be: null"
  }

  assert {
    condition     = local.domain_list == ""
    error_message = "Should be: \"\""
  }
}

run "waf_and_rotate_lambda" {
  command = plan

  assert {
    condition     = aws_secretsmanager_secret.origin-verify-secret[""].name == "${var.application}-${var.environment}-origin-verify-header-secret"
    error_message = "Invalid name for aws_secretsmanager_secret.origin-verify-secret"
  }

  assert {
    condition     = aws_secretsmanager_secret.origin-verify-secret[""].description == "Secret used for Origin verification in WAF rules"
    error_message = "Invalid description for aws_secretsmanager_secret.origin-verify-secret"
  }

  assert {
    condition     = aws_wafv2_web_acl.waf-acl[""].name == "${var.application}-${var.environment}-ACL"
    error_message = "Invalid name for aws_wafv2_web_acl.waf-acl"
  }

  assert {
    condition     = aws_wafv2_web_acl.waf-acl[""].description == "CloudFront Origin Verify"
    error_message = "Invalid description for aws_wafv2_web_acl.waf-acl"
  }

  assert {
    condition     = aws_wafv2_web_acl.waf-acl[""].scope == "REGIONAL"
    error_message = "Invalid scope for aws_wafv2_web_acl.waf-acl"
  }

  assert {
    condition     = aws_wafv2_web_acl.waf-acl[""].default_action[0].block != null
    error_message = "Invalid default_action for aws_wafv2_web_acl.waf-acl"
  }

  assert {
    condition     = aws_wafv2_web_acl.waf-acl[""].visibility_config[0].cloudwatch_metrics_enabled == true
    error_message = "Invalid visibility_config for aws_wafv2_web_acl.waf-acl"
  }

  assert {
    condition     = aws_wafv2_web_acl.waf-acl[""].visibility_config[0].metric_name == "${var.application}-${var.environment}-XOriginVerify"
    error_message = "Invalid metric_name in visibility_config for aws_wafv2_web_acl.waf-acl"
  }

  assert {
    condition     = aws_wafv2_web_acl.waf-acl[""].visibility_config[0].sampled_requests_enabled == true
    error_message = "Invalid sampled_requests_enabled in visibility_config for aws_wafv2_web_acl.waf-acl"
  }

  assert {
    condition     = length([for r in aws_wafv2_web_acl.waf-acl[""].rule : r.name if r.name == "${var.application}-${var.environment}-XOriginVerify"]) == 1
    error_message = "Invalid rule name for aws_wafv2_web_acl.waf-acl"
  }

  assert {
    condition     = [for r in aws_wafv2_web_acl.waf-acl[""].rule : r.priority if r.name == "${var.application}-${var.environment}-XOriginVerify"][0] == 0
    error_message = "Invalid priority for rule ${var.application}-${var.environment}-XOriginVerify in aws_wafv2_web_acl.waf-acl"
  }

  assert {
    condition     = length([for r in aws_wafv2_web_acl.waf-acl[""].rule : try(r.action[0].allow, null) if r.name == "${var.application}-${var.environment}-XOriginVerify" && try(r.action[0].allow, null) != null]) == 1
    error_message = "Invalid rule action for aws_wafv2_web_acl.waf-acl"
  }

  assert {
    condition     = length([for r in aws_wafv2_web_acl.waf-acl[""].rule : r.visibility_config[0] if r.name == "${var.application}-${var.environment}-XOriginVerify" && r.visibility_config[0].cloudwatch_metrics_enabled == true]) == 1
    error_message = "Invalid visibility_config for aws_wafv2_web_acl.waf-acl rule"
  }

  assert {
    condition     = length([for r in aws_wafv2_web_acl.waf-acl[""].rule : r.visibility_config[0] if r.name == "${var.application}-${var.environment}-XOriginVerify" && r.visibility_config[0].metric_name == "${var.application}-${var.environment}-XMetric"]) == 1
    error_message = "Invalid metric_name in visibility_config for aws_wafv2_web_acl.waf-acl rule"
  }

  assert {
    condition     = length([for r in aws_wafv2_web_acl.waf-acl[""].rule : r.visibility_config[0] if r.name == "${var.application}-${var.environment}-XOriginVerify" && r.visibility_config[0].sampled_requests_enabled == true]) == 1
    error_message = "Invalid sampled_requests_enabled in visibility_config for aws_wafv2_web_acl.waf-acl rule"
  }

  # --- Testing of the WAF rule statement ---

  assert {
    condition = length(
      [for r in aws_wafv2_web_acl.waf-acl[""].rule :
        r.name if can(regex("${var.application}-${var.environment}-XOriginVerify", r.name))
      ]
    ) > 0
    error_message = "The rule named ${var.application}-${var.environment}-XOriginVerify does not exist in aws_wafv2_web_acl.waf-acl"
  }

  assert {
    condition = alltrue([
      for r in aws_wafv2_web_acl.waf-acl[""].rule :
      r.name == "${var.application}-${var.environment}-XOriginVerify" ? (
        try(r.statement[0].not_statement[0].statement[0].byte_match_statement[0].field_to_match[0].single_header[0].name, "") == "x-origin-verify"
      ) : true
    ])
    error_message = "Statement's single header name is incorrect"
  }

  assert {
    condition = alltrue([
      for r in aws_wafv2_web_acl.waf-acl[""].rule :
      r.name == "${var.application}-${var.environment}-XOriginVerify" ? (
        try(r.statement[0].not_statement[0].statement[0].byte_match_statement[0].positional_constraint, "") == "EXACTLY"
      ) : true
    ])
    error_message = "First statement positional_constraint should be 'EXACTLY'"
  }

  # --- End testing of the WAF rule statement ---

  assert {
    condition     = aws_lambda_function.origin-secret-rotate-function[""].function_name == "${var.application}-${var.environment}-origin-secret-rotate"
    error_message = "Invalid name for aws_lambda_function.origin-secret-rotate-function"
  }

  assert {
    condition     = aws_lambda_function.origin-secret-rotate-function[""].description == "Secrets Manager Rotation Lambda Function"
    error_message = "Invalid description for aws_lambda_function.origin-secret-rotate-function"
  }

  assert {
    condition     = aws_lambda_function.origin-secret-rotate-function[""].handler == "rotate_secret_lambda.lambda_handler"
    error_message = "Invalid handler for aws_lambda_function.origin-secret-rotate-function"
  }

  assert {
    condition     = aws_lambda_function.origin-secret-rotate-function[""].runtime == "python3.9"
    error_message = "Invalid runtime for aws_lambda_function.origin-secret-rotate-function"
  }

  assert {
    condition     = aws_lambda_function.origin-secret-rotate-function[""].timeout == 300
    error_message = "Invalid timeout for aws_lambda_function.origin-secret-rotate-function"
  }

  assert {
    condition     = aws_lambda_function.origin-secret-rotate-function[""].environment[0].variables.WAFACLNAME == split("|", aws_wafv2_web_acl.waf-acl[""].name)[0]
    error_message = "Invalid WAFACLNAME environment variable for aws_lambda_function.origin-secret-rotate-function"
  }

  assert {
    condition     = aws_lambda_function.origin-secret-rotate-function[""].environment[0].variables.WAFRULEPRI == "0"
    error_message = "Invalid WAFRULEPRI environment variable for aws_lambda_function.origin-secret-rotate-function"
  }

  assert {
    condition     = aws_lambda_function.origin-secret-rotate-function[""].environment[0].variables.HEADERNAME == "x-origin-verify"
    error_message = "Invalid HEADERNAME environment variable for aws_lambda_function.origin-secret-rotate-function"
  }

  assert {
    condition     = aws_lambda_function.origin-secret-rotate-function[""].environment[0].variables.APPLICATION == var.application
    error_message = "Invalid APPLICATION environment variable for aws_lambda_function.origin-secret-rotate-function"
  }

  assert {
    condition     = aws_lambda_function.origin-secret-rotate-function[""].environment[0].variables.ENVIRONMENT == var.environment
    error_message = "Invalid ENVIRONMENT environment variable for aws_lambda_function.origin-secret-rotate-function"
  }

  assert {
    condition     = aws_lambda_function.origin-secret-rotate-function[""].environment[0].variables.ROLEARN == "arn:aws:iam::${var.dns_account_id}:role/dbt_platform_cloudfront_token_rotation"
    error_message = "Invalid ROLEARN environment variable for aws_lambda_function.origin-secret-rotate-function"
  }

  assert {
    condition     = aws_lambda_function.origin-secret-rotate-function[""].environment[0].variables.AWS_ACCOUNT == data.aws_caller_identity.current.account_id
    error_message = "Invalid AWS_ACCOUNT environment variable for aws_lambda_function.origin-secret-rotate-function"
  }

  assert {
    condition     = aws_lambda_function.origin-secret-rotate-function[""].environment[0].variables.SLACK_TOKEN == data.aws_ssm_parameter.slack_token.value
    error_message = "Invalid SLACK_TOKEN environment variable for aws_lambda_function.origin-secret-rotate-function"
  }

  assert {
    condition     = aws_lambda_function.origin-secret-rotate-function[""].environment[0].variables.SLACK_CHANNEL == local.config_with_defaults.slack_alert_channel_alb_secret_rotation
    error_message = "Invalid SLACK_CHANNEL environment variable for aws_lambda_function.origin-secret-rotate-function"
  }

  assert {
    condition     = aws_lambda_permission.rotate-function-invoke-permission[""].statement_id == "AllowSecretsManagerInvocation"
    error_message = "Invalid statement_id for aws_lambda_permission.rotate-function-invoke-permission"
  }

  assert {
    condition     = aws_lambda_permission.rotate-function-invoke-permission[""].action == "lambda:InvokeFunction"
    error_message = "Invalid action for aws_lambda_permission.rotate-function-invoke-permission"
  }

  assert {
    condition     = aws_lambda_permission.rotate-function-invoke-permission[""].function_name == aws_lambda_function.origin-secret-rotate-function[""].function_name
    error_message = "Invalid function_name for aws_lambda_permission.rotate-function-invoke-permission"
  }

  assert {
    condition     = aws_lambda_permission.rotate-function-invoke-permission[""].principal == "secretsmanager.amazonaws.com"
    error_message = "Invalid principal for aws_lambda_permission.rotate-function-invoke-permission"
  }

  assert {
    condition     = aws_iam_role.origin-secret-rotate-execution-role[""].name == "${var.application}-${var.environment}-origin-secret-rotate-role"
    error_message = "Invalid name for aws_iam_role.origin-secret-rotate-execution-role"
  }

  assert {
    condition     = aws_iam_role.origin-secret-rotate-execution-role[""].assume_role_policy != null
    error_message = "Invalid assume_role_policy for aws_iam_role.origin-secret-rotate-execution-role"
  }

  # Cannot assert against the arn in a plan. Requires an apply to evaluate.

  assert {
    condition     = aws_secretsmanager_secret_rotation.origin-verify-rotate-schedule[""].rotation_rules[0].automatically_after_days == 7
    error_message = "Invalid rotation_rules.automatically_after_days for aws_secretsmanager_secret_rotation.origin-verify-rotate-schedule"
  }
}

run "waf_and_rotate_lambda_no_cdn_domains" {
  command = plan

  variables {
    config = {
      cdn_domains_list = null
    }
  }

  assert {
    condition     = length(aws_secretsmanager_secret.origin-verify-secret) == 0
    error_message = "Resource should not be created"
  }

  assert {
    condition     = length(aws_secretsmanager_secret_policy.secret_policy) == 0
    error_message = "No secret should be created"
  }

  assert {
    condition     = length(aws_kms_key.origin_verify_secret_key) == 0
    error_message = "No secret should be created"
  }

  assert {
    condition     = length(aws_kms_alias.origin_verify_secret_key_alias) == 0
    error_message = "No secret should be created"
  }

  assert {
    condition     = length(aws_secretsmanager_secret_rotation.origin-verify-rotate-schedule) == 0
    error_message = "No secret should be created"
  }
  assert {
    condition     = length(aws_wafv2_web_acl.waf-acl) == 0
    error_message = "No secret should be created"
  }

  assert {
    condition     = length(aws_lambda_function.origin-secret-rotate-function) == 0
    error_message = "No secret should be created"
  }

  assert {
    condition     = length(aws_iam_role.origin-secret-rotate-execution-role) == 0
    error_message = "No secret should be created"
  }

  assert {
    condition     = length(aws_lambda_permission.rotate-function-invoke-permission) == 0
    error_message = "No secret should be created"
  }

  assert {
    condition     = length(aws_iam_role_policy.origin_secret_rotate_policy) == 0
    error_message = "No secret should be created"
  }
}

run "waf_and_rotate_lambda_cdn_domains_disabled" {
  command = plan

  variables {
    config = {
      cdn_domains_list = {
        "web.dev.my-application.uktrade.digital" : ["internal.web", "my-application.uktrade.digital", "disable_cdn"]
      }
    }
  }

  assert {
    condition     = length(aws_secretsmanager_secret.origin-verify-secret) == 0
    error_message = "Resource should not be created"
  }

  assert {
    condition     = length(aws_secretsmanager_secret_policy.secret_policy) == 0
    error_message = "No secret should be created"
  }

  assert {
    condition     = length(aws_kms_key.origin_verify_secret_key) == 0
    error_message = "No secret should be created"
  }

  assert {
    condition     = length(aws_kms_alias.origin_verify_secret_key_alias) == 0
    error_message = "No secret should be created"
  }

  assert {
    condition     = length(aws_secretsmanager_secret_rotation.origin-verify-rotate-schedule) == 0
    error_message = "No secret should be created"
  }
  assert {
    condition     = length(aws_wafv2_web_acl.waf-acl) == 0
    error_message = "No secret should be created"
  }

  assert {
    condition     = length(aws_lambda_function.origin-secret-rotate-function) == 0
    error_message = "No secret should be created"
  }

  assert {
    condition     = length(aws_iam_role.origin-secret-rotate-execution-role) == 0
    error_message = "No secret should be created"
  }

  assert {
    condition     = length(aws_lambda_permission.rotate-function-invoke-permission) == 0
    error_message = "No secret should be created"
  }

  assert {
    condition     = length(aws_iam_role_policy.origin_secret_rotate_policy) == 0
    error_message = "No secret should be created"
  }
}
