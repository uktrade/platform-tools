mock_provider "aws" {}

override_data {
  target = data.aws_caller_identity.current
  values = {
    account_id = "001122334455"
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
  target = data.aws_subnets.private-subnets
  values = {
    ids = ["subnet-000111222aaabbb01", "subnet-000111222aaabbb02", "subnet-000111222aaabbb03"]
  }
}

override_data {
  target = data.aws_ssm_parameter.log-destination-arn
  values = {
    value = "{\"prod\":\"arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_prod\", \"dev\":\"arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_dev\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.assume_ecstask_role
  values = {
    json = "{\"Sid\": \"AllowAssumeECSTaskRole\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.conduit_task_role_access
  values = {
    json = <<EOT
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ssmmessages:CreateControlChannel",
        "ssmmessages:OpenControlChannel",
        "ssmmessages:CreateDataChannel",
        "ssmmessages:OpenDataChannel"
      ],
      "Resource": "*"
    }
  ]
}
EOT
  }
}


run "test_create_opensearch" {
  command = plan

  variables {
    application = "my_app"
    environment = "my_env"
    name        = "my_name"
    vpc_name    = "terraform-tests-vpc"

    config = {
      engine                      = "2.5"
      instance                    = "t3.small.search"
      instances                   = 1
      volume_size                 = 80
      enable_ha                   = false
      password_special_characters = "-_.,()"
      urlencode_password          = false
    }
  }

  assert {
    condition     = aws_opensearch_domain.this.domain_name == "my-env-my-name"
    error_message = "Should be: 'my-env-my-name'"
  }

  assert {
    condition     = aws_opensearch_domain.this.engine_version == "OpenSearch_2.5"
    error_message = "Should be: 'OpenSearch_2.5'"
  }

  assert {
    condition     = aws_opensearch_domain.this.cluster_config[0].dedicated_master_type == null
    error_message = "Should be: null"
  }

  assert {
    condition     = aws_opensearch_domain.this.cluster_config[0].dedicated_master_enabled == false
    error_message = "Should be: false"
  }

  assert {
    condition     = aws_opensearch_domain.this.cluster_config[0].dedicated_master_count == null
    error_message = "Should be: null"
  }

  assert {
    condition     = aws_opensearch_domain.this.cluster_config[0].instance_type == "t3.small.search"
    error_message = "Should be: 't3.small.search'"
  }

  assert {
    condition     = aws_opensearch_domain.this.cluster_config[0].instance_count == 1
    error_message = "Should be: 1"
  }

  assert {
    condition     = aws_opensearch_domain.this.ebs_options[0].volume_size == 80
    error_message = "Should be: 80"
  }

  assert {
    condition     = aws_opensearch_domain.this.ebs_options[0].volume_type == "gp2"
    error_message = "Should be: 'gp2'"
  }

  assert {
    condition     = aws_opensearch_domain.this.auto_tune_options[0].desired_state == "DISABLED"
    error_message = "Should be: 'DISABLED'"
  }

  assert {
    condition     = aws_opensearch_domain.this.tags.application == "my_app"
    error_message = "application tag was not as expected"
  }

  assert {
    condition     = aws_opensearch_domain.this.tags.environment == "my_env"
    error_message = "environment tag was not as expected"
  }

  assert {
    condition     = aws_opensearch_domain.this.tags.managed-by == "DBT Platform - Terraform"
    error_message = "managed-by tag was not as expected"
  }

  assert {
    condition     = aws_opensearch_domain.this.tags.copilot-application == "my_app"
    error_message = "copilot-application tag was not as expected"
  }

  assert {
    condition     = aws_opensearch_domain.this.tags.copilot-environment == "my_env"
    error_message = "copilot-environment tag was not as expected"
  }

  assert {
    condition     = aws_ssm_parameter.opensearch_endpoint.name == "/copilot/my_app/my_env/secrets/MY_NAME_ENDPOINT"
    error_message = "Should be: '/copilot/my_app/my_env/secrets/MY_NAME_ENDPOINT'"
  }

  assert {
    condition     = aws_ssm_parameter.opensearch_endpoint.description == "opensearch_password"
    error_message = "Should be: 'opensearch_password'"
  }

  assert {
    condition     = aws_cloudwatch_log_group.opensearch_log_group_index_slow_logs.retention_in_days == 7
    error_message = "Should be: 7"
  }

  assert {
    condition     = aws_cloudwatch_log_group.opensearch_log_group_search_slow_logs.retention_in_days == 7
    error_message = "Should be: 7"
  }

  assert {
    condition     = aws_cloudwatch_log_group.opensearch_log_group_es_application_logs.retention_in_days == 7
    error_message = "Should be: 7"
  }

  assert {
    condition     = aws_cloudwatch_log_group.opensearch_log_group_audit_logs.retention_in_days == 7
    error_message = "Should be: 7"
  }
}

run "test_create_opensearch_x_large_ha" {
  command = plan

  variables {
    application = "my_app"
    environment = "my_env"
    name        = "my_name"
    vpc_name    = "terraform-tests-vpc"

    config = {
      name        = "my_name"
      engine      = "2.5"
      instance    = "m6g.2xlarge.search"
      instances   = 2
      volume_size = 1500
      enable_ha   = true
    }
  }

  assert {
    condition     = aws_opensearch_domain.this.cluster_config[0].dedicated_master_type == "m6g.2xlarge.search"
    error_message = "Should be: m6g.2xlarge.search"
  }

  assert {
    condition     = aws_opensearch_domain.this.cluster_config[0].dedicated_master_enabled == true
    error_message = "Should be: true"
  }

  assert {
    condition     = aws_opensearch_domain.this.cluster_config[0].dedicated_master_count == 3
    error_message = "Should be: 3"
  }

  assert {
    condition     = aws_opensearch_domain.this.cluster_config[0].instance_type == "m6g.2xlarge.search"
    error_message = "Should be: 'm6g.2xlarge.search'"
  }

  assert {
    condition     = aws_opensearch_domain.this.cluster_config[0].instance_count == 2
    error_message = "Should be: 2"
  }

  assert {
    condition     = aws_opensearch_domain.this.ebs_options[0].volume_size == 1500
    error_message = "Should be: 1500"
  }

  assert {
    condition     = aws_opensearch_domain.this.auto_tune_options[0].desired_state == "ENABLED"
    error_message = "Should be: 'ENABLED'"
  }

  assert {
    condition     = aws_ssm_parameter.opensearch_endpoint.name == "/copilot/my_app/my_env/secrets/MY_NAME_ENDPOINT"
    error_message = "Should be: '/copilot/my_app/my_env/secrets/MY_NAME_ENDPOINT'"
  }

  assert {
    condition     = aws_ssm_parameter.opensearch_endpoint.description == "opensearch_password"
    error_message = "Should be: 'opensearch_password'"
  }
}

run "test_overrides" {
  command = plan

  variables {
    application = "my_app"
    environment = "my_env"
    name        = "my_name"
    vpc_name    = "terraform-tests-vpc"

    config = {
      name                              = "my_name"
      engine                            = "2.5"
      instance                          = "t3.small.search"
      instances                         = 1
      volume_size                       = 80
      enable_ha                         = false
      ebs_volume_type                   = "gp3"
      ebs_throughput                    = 500
      index_slow_log_retention_in_days  = 3
      search_slow_log_retention_in_days = 14
      es_app_log_retention_in_days      = 30
      audit_log_retention_in_days       = 1096
    }
  }

  assert {
    condition     = aws_opensearch_domain.this.ebs_options[0].volume_type == "gp3"
    error_message = "Should be: 'gp3'"
  }

  assert {
    condition     = aws_opensearch_domain.this.ebs_options[0].throughput == 500
    error_message = "Should be: 500"
  }

  assert {
    condition     = aws_cloudwatch_log_group.opensearch_log_group_index_slow_logs.retention_in_days == 3
    error_message = "Should be: 3"
  }

  assert {
    condition     = aws_cloudwatch_log_group.opensearch_log_group_search_slow_logs.retention_in_days == 14
    error_message = "Should be: 14"
  }

  assert {
    condition     = aws_cloudwatch_log_group.opensearch_log_group_es_application_logs.retention_in_days == 30
    error_message = "Should be: 30"
  }

  assert {
    condition     = aws_cloudwatch_log_group.opensearch_log_group_audit_logs.retention_in_days == 1096
    error_message = "Should be: 1096"
  }
}

run "test_volume_type_validation" {
  command = plan

  variables {
    application = "my_app"
    environment = "my_env"
    name        = "my_name"
    vpc_name    = "terraform-tests-vpc"

    config = {
      name                              = "my_name"
      engine                            = "2.5"
      instance                          = "t3.small.search"
      instances                         = 1
      volume_size                       = 80
      enable_ha                         = false
      ebs_volume_type                   = "banana"
      index_slow_log_retention_in_days  = 9
      search_slow_log_retention_in_days = 10
      es_app_log_retention_in_days      = 13
      audit_log_retention_in_days       = 37
    }
  }

  expect_failures = [
    var.config.ebs_volume_type,
    var.config.index_slow_log_retention_in_days,
    var.config.search_slow_log_retention_in_days,
    var.config.es_app_log_retention_in_days,
    var.config.audit_log_retention_in_days,
  ]
}

run "test_domain_name_truncation" {
  command = plan

  variables {
    application = "my_app"
    environment = "my_prod_env"
    name        = "my_really_large_name"
    vpc_name    = "terraform-tests-vpc"

    config = {
      engine      = "2.5"
      instance    = "t3.small.search"
      instances   = 1
      volume_size = 80
      enable_ha   = false
    }
  }

  assert {
    condition     = aws_opensearch_domain.this.domain_name == "my-prod-env-my-really-large-"
    error_message = "Should be: 'my-prod-env-my-really-large-'"
  }
}

run "test_create_cloudwatch_subscription_filters" {
  command = plan

  variables {
    application = "my_app"
    environment = "my_env"
    name        = "my_name"
    vpc_name    = "terraform-tests-vpc"

    config = {
      engine      = "2.5"
      instance    = "t3.small.search"
      instances   = 1
      volume_size = 80
      enable_ha   = false
    }
  }

  assert {
    condition     = aws_cloudwatch_log_subscription_filter.opensearch_log_group_index_slow_logs.name == "/aws/opensearch/my_app/my_env/my_name/opensearch_log_group_index_slow"
    error_message = "Cloudwatch log subscription filter name for cloudwatch log 'opensearch_log_group_index_slow_logs'Should be: '/aws/opensearch/my_app/my_env/my_name/opensearch_log_group_index_slow'"
  }

  assert {
    condition     = aws_cloudwatch_log_subscription_filter.opensearch_log_group_index_slow_logs.destination_arn == "arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_dev"
    error_message = "Cloudwatch log subscription filter destination ARN for cloudwatch log 'opensearch_log_group_index_slow_logs'Should be: 'arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_dev'"
  }

  assert {
    condition     = aws_cloudwatch_log_subscription_filter.opensearch_log_group_search_slow_logs.name == "/aws/opensearch/my_app/my_env/my_name/opensearch_log_group_search_slow"
    error_message = "Cloudwatch log subscription filter name for cloudwatch log 'opensearch_log_group_search_slow_logs'Should be: '/aws/opensearch/my_app/my_env/my_name/opensearch_log_group_search_slow'"
  }

  assert {
    condition     = aws_cloudwatch_log_subscription_filter.opensearch_log_group_search_slow_logs.destination_arn == "arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_dev"
    error_message = "Cloudwatch log subscription filter destination ARN for cloudwatch log 'opensearch_log_group_search_slow_logs'Should be: 'arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_dev'"
  }

  assert {
    condition     = aws_cloudwatch_log_subscription_filter.opensearch_log_group_es_application_logs.name == "/aws/opensearch/my_app/my_env/my_name/opensearch_log_group_es_application"
    error_message = "Cloudwatch log subscription filter name for cloudwatch log 'opensearch_log_group_es_application_logs'Should be: '/aws/opensearch/my_app/my_env/my_name/opensearch_log_group_es_application'"
  }

  assert {
    condition     = aws_cloudwatch_log_subscription_filter.opensearch_log_group_es_application_logs.destination_arn == "arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_dev"
    error_message = "Cloudwatch log subscription filter destination ARN for cloudwatch log 'opensearch_log_group_es_application_logs'Should be: 'arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_dev'"
  }

  assert {
    condition     = aws_cloudwatch_log_subscription_filter.opensearch_log_group_audit_logs.name == "/aws/opensearch/my_app/my_env/my_name/opensearch_log_group_audit"
    error_message = "Cloudwatch log subscription filter name for cloudwatch log 'opensearch_log_group_audit_logs'Should be: '/aws/opensearch/my_app/my_env/my_name/opensearch_log_group_audit'"
  }

  assert {
    condition     = aws_cloudwatch_log_subscription_filter.opensearch_log_group_audit_logs.destination_arn == "arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_dev"
    error_message = "Cloudwatch log subscription filter destination ARN for cloudwatch log 'opensearch_log_group_audit_logs'Should be: 'arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_dev'"
  }

  assert {
    condition     = aws_cloudwatch_log_subscription_filter.opensearch_log_group_index_slow_logs.log_group_name == "/aws/opensearch/my-env-my-name/index-slow"
    error_message = "Cloudwatch log subscription filter log group name for cloudwatch log 'opensearch_log_group_index_slow_logs'Should be: '/aws/opensearch/my-env-my-name/index-slow'"
  }

  assert {
    condition     = aws_cloudwatch_log_subscription_filter.opensearch_log_group_search_slow_logs.log_group_name == "/aws/opensearch/my-env-my-name/search-slow"
    error_message = "Cloudwatch log subscription filter log group name for cloudwatch log 'opensearch_log_group_search_slow_logs'Should be: '/aws/opensearch/my-env-my-name/search-slow'"
  }

  assert {
    condition     = aws_cloudwatch_log_subscription_filter.opensearch_log_group_es_application_logs.log_group_name == "/aws/opensearch/my-env-my-name/es-application"
    error_message = "Cloudwatch log subscription filter log group name for cloudwatch log 'opensearch_log_group_es_application_logs'Should be: '/aws/opensearch/my-env-my-name/es-application'"
  }

  assert {
    condition     = aws_cloudwatch_log_subscription_filter.opensearch_log_group_audit_logs.log_group_name == "/aws/opensearch/my-env-my-name/audit"
    error_message = "Cloudwatch log subscription filter log group name for cloudwatch log 'opensearch_log_group_audit_logs'Should be: '/aws/opensearch/my-env-my-name/audit'"
  }
}

run "aws_kms_key_unit_test" {

  command = plan

  variables {
    application = "my_app"
    environment = "my_env"
    name        = "my_name"
    vpc_name    = "terraform-tests-vpc"

    config = {
      engine      = "2.5"
      instance    = "t3.small.search"
      instances   = 1
      volume_size = 80
      enable_ha   = false
    }
  }

  assert {
    condition     = aws_kms_key.cloudwatch_log_group_kms_key.description == "KMS Key for my_name-my_env CloudWatch Log encryption"
    error_message = "Should be: KMS Key for my_name-my_env CloudWatch Log encryption"
  }

  assert {
    condition     = aws_kms_key.cloudwatch_log_group_kms_key.enable_key_rotation == true
    error_message = "Should be: true"
  }

  assert {
    condition     = aws_iam_role.conduit_ecs_task_role.name == "my_name-my_app-my_env-conduitEcsTask"
    error_message = "Should be: my_name-my_app-my_env-conduitEcsTask"
  }

  # Check that the correct aws_iam_policy_document is used from the mocked data json
  assert {
    condition     = aws_iam_role.conduit_ecs_task_role.assume_role_policy == "{\"Sid\": \"AllowAssumeECSTaskRole\"}"
    error_message = "Should be: {\"Sid\": \"AllowAssumeECSTaskRole\"}"
  }

  # Check the contents of the policy document
  assert {
    condition     = contains(data.aws_iam_policy_document.assume_ecstask_role.statement[0].actions, "sts:AssumeRole")
    error_message = "Should be: sts:AssumeRole"
  }
  assert {
    condition     = data.aws_iam_policy_document.assume_ecstask_role.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = strcontains(jsonencode(data.aws_iam_policy_document.assume_ecstask_role.statement[0].principals), "ecs-tasks.amazonaws.com")
    error_message = "Should be: ecs-tasks.amazonaws.com"
  }

  # Check kms access role policy
  assert {
    condition     = aws_iam_role_policy.kms_access_for_conduit_ecs_task.name == "AllowReadingofCMKSecrets"
    error_message = "Should be: 'AllowReadingofCMKSecrets'"
  }
  assert {
    condition     = aws_iam_role_policy.kms_access_for_conduit_ecs_task.role == "my_name-my_app-my_env-conduitEcsTask"
    error_message = "Should be: 'my_name-my_app-my_env-conduitEcsTask'"
  }
}
