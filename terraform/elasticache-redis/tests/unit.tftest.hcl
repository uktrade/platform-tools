mock_provider "aws" {}

variables {
  vpc_name    = "sandbox-elasticache-redis"
  application = "test-application"
  environment = "test-environment"
  name        = "test-redis"
  config = {
    "engine" = "6.2",
    "plan"   = "small",
  }
  expected_tags = {
    application         = "test-application"
    environment         = "test-environment"
    managed-by          = "DBT Platform - Terraform"
    copilot-application = "test-application"
    copilot-environment = "test-environment"
  }
}

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

run "aws_elasticache_replication_group_unit_test" {
  command = plan

  ### Test aws_elasticache_replication_group resource ###
  assert {
    condition     = aws_elasticache_replication_group.redis.replication_group_id == "test-redis-test-environment"
    error_message = "Invalid config for aws_elasticache_replication_group replication_group_id"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.subnet_group_name == "test-redis-test-environment-cache-subnet"
    error_message = "Invalid config for aws_elasticache_replication_group subnet_group_name"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.engine == "redis"
    error_message = "Invalid config for aws_elasticache_replication_group engine"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.engine_version == "6.2"
    error_message = "Invalid config for aws_elasticache_replication_group engine_version"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.num_node_groups == 1
    error_message = "Invalid config for aws_elasticache_replication_group num_node_groups"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.replicas_per_node_group == 1
    error_message = "Invalid config for aws_elasticache_replication_group replicas_per_node_group"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.transit_encryption_enabled == true
    error_message = "Invalid config for aws_elasticache_replication_group transit_encryption_enabled"
  }


  # Set to a string due to changes in this release: https://github.com/hashicorp/terraform-provider-aws/releases/tag/v5.82.0  If this test fails, run terraform init -upgrade in the module directory
  assert {
    condition     = aws_elasticache_replication_group.redis.at_rest_encryption_enabled == "true"
    error_message = "Invalid config for aws_elasticache_replication_group at_rest_encryption_enabled"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.apply_immediately == false
    error_message = "Invalid config for aws_elasticache_replication_group apply_immediately"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.automatic_failover_enabled == false
    error_message = "Invalid config for aws_elasticache_replication_group automatic_failover_enabled"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.multi_az_enabled == false
    error_message = "Invalid config for aws_elasticache_replication_group multi_az_enabled"
  }

  # Cannot test for the default on a plan
  # aws_elasticache_replication_group.redis.auth_token_update_strategy == "ROTATE"

  assert {
    condition     = [for el in aws_elasticache_replication_group.redis.log_delivery_configuration : el.destination if el.log_type == "engine-log"][0] == "/aws/elasticache/test-redis/test-environment/test-redisRedis/engine"
    error_message = "Invalid config for aws_elasticache_replication_group log_delivery_configuration"
  }

  assert {
    condition     = [for el in aws_elasticache_replication_group.redis.log_delivery_configuration : el.destination if el.log_type == "slow-log"][0] == "/aws/elasticache/test-redis/test-environment/test-redisRedis/slow"
    error_message = "Invalid config for aws_elasticache_replication_group log_delivery_configuration"
  }

  assert {
    condition     = jsonencode(aws_elasticache_replication_group.redis.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }
}

run "aws_elasticache_replication_group_unit_test2" {
  command = plan

  variables {
    config = {
      "engine"                     = "7.1",
      "plan"                       = "small",
      "instance"                   = "test-instance",
      "replicas"                   = 2,
      "apply_immediately"          = true,
      "automatic_failover_enabled" = true,
      "multi_az_enabled"           = true,
    }
  }

  ### Test aws_elasticache_replication_group resource ###
  assert {
    condition     = aws_elasticache_replication_group.redis.engine == "redis"
    error_message = "Invalid config for aws_elasticache_replication_group engine"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.engine_version == "7.1"
    error_message = "Invalid config for aws_elasticache_replication_group engine_version"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.num_node_groups == 1
    error_message = "Invalid config for aws_elasticache_replication_group num_node_groups"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.replicas_per_node_group == 2
    error_message = "Invalid config for aws_elasticache_replication_group replicas_per_node_group"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.transit_encryption_enabled == true
    error_message = "Invalid config for aws_elasticache_replication_group transit_encryption_enabled"
  }

  # Set to a string due to changes in this release: https://github.com/hashicorp/terraform-provider-aws/releases/tag/v5.82.0  If this test fails, run terraform init -upgrade in the module directory
  assert {
    condition     = aws_elasticache_replication_group.redis.at_rest_encryption_enabled == "true"
    error_message = "Invalid config for aws_elasticache_replication_group at_rest_encryption_enabled"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.apply_immediately == true
    error_message = "Invalid config for aws_elasticache_replication_group apply_immediately"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.automatic_failover_enabled == true
    error_message = "Invalid config for aws_elasticache_replication_group automatic_failover_enabled"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.multi_az_enabled == true
    error_message = "Invalid config for aws_elasticache_replication_group multi_az_enabled"
  }
}

run "aws_security_group_unit_test" {
  command = plan

  ### Test aws_security_group resource ###
  assert {
    condition     = aws_security_group.redis.name == "test-redis-test-environment-redis-security-group"
    error_message = "Invalid config for aws_security_group name"
  }

  # Cannot test for the default on a plan
  # aws_security_group.redis.revoke_rules_on_delete == false

  assert {
    condition     = jsonencode(aws_security_group.redis.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }
}

run "aws_ssm_parameter_endpoint_unit_test" {
  command = plan

  assert {
    condition     = aws_ssm_parameter.endpoint.name == "/copilot/test-application/test-environment/secrets/TEST_REDIS_ENDPOINT"
    error_message = "Invalid config for aws_ssm_parameter name"
  }

  assert {
    condition     = aws_ssm_parameter.endpoint.type == "SecureString"
    error_message = "Invalid config for aws_ssm_parameter type"
  }

  assert {
    condition     = jsonencode(aws_ssm_parameter.endpoint.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }

  ### test for aws_ssm_parameter.endpoint.key_id == aws_kms_key.ssm_redis_endpoint.arn can only be run as part of an terraform apply
}

run "aws_ssm_parameter_endpoint_short_unit_test" {
  command = plan

  assert {
    condition     = aws_ssm_parameter.endpoint_short.name == "/copilot/test-application/test-environment/secrets/TEST_REDIS"
    error_message = "Invalid config for aws_ssm_parameter name"
  }

  assert {
    condition     = aws_ssm_parameter.endpoint_short.type == "SecureString"
    error_message = "Invalid config for aws_ssm_parameter type"
  }

  assert {
    condition     = jsonencode(aws_ssm_parameter.endpoint_short.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }

  ### test for aws_ssm_parameter.endpoint_short.key_id == aws_kms_key.ssm_redis_endpoint.arn can only be run as part of an terraform apply
}

run "aws_ssm_parameter_redis_url_unit_test" {
  command = plan

  assert {
    condition     = aws_ssm_parameter.redis_url.name == "/copilot/test-application/test-environment/secrets/TEST_REDIS_URL"
    error_message = "Invalid config for aws_ssm_parameter name"
  }

  assert {
    condition     = aws_ssm_parameter.redis_url.type == "SecureString"
    error_message = "Invalid config for aws_ssm_parameter type"
  }

  assert {
    condition     = jsonencode(aws_ssm_parameter.redis_url.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }

  ### test for aws_ssm_parameter.redis_url.key_id == aws_kms_key.ssm_redis_endpoint.arn can only be run as part of an terraform apply
}

run "aws_kms_key_unit_test" {
  command = plan

  assert {
    condition     = aws_kms_key.ssm_redis_endpoint.description == "KMS key for test-redis-test-application-test-environment-redis-cluster SSM parameters"
    error_message = "Should be"
  }

  assert {
    condition     = aws_kms_key.ssm_redis_endpoint.deletion_window_in_days == 10
    error_message = "Should be: 10"
  }

  assert {
    condition     = aws_kms_key.ssm_redis_endpoint.enable_key_rotation == true
    error_message = "Should be: true"
  }

  assert {
    condition     = jsonencode(aws_kms_key.ssm_redis_endpoint.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }

  assert {
    condition     = aws_kms_key.redis-log-group-kms-key.description == "KMS Key for test-redis-test-environment Redis Log encryption"
    error_message = "Should be: KMS key for test-redis-test-environment Redis Log encryption"
  }

  assert {
    condition     = aws_kms_key.redis-log-group-kms-key.enable_key_rotation == true
    error_message = "Should be: true"
  }

  assert {
    condition     = jsonencode(aws_kms_key.redis-log-group-kms-key.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }


}

run "aws_cloudwatch_log_group_unit_test" {
  command = plan

  ### Test aws_cloudwatch_log_group slow resource ###
  assert {
    condition     = aws_cloudwatch_log_group.redis-slow-log-group.name == "/aws/elasticache/test-redis/test-environment/test-redisRedis/slow"
    error_message = "Invalid config for aws_cloudwatch_log_group name"
  }

  assert {
    condition     = aws_cloudwatch_log_group.redis-slow-log-group.retention_in_days == 7
    error_message = "Invalid config for aws_cloudwatch_log_group retention_in_days"
  }

  # Cannot test for the default on a plan
  # aws_cloudwatch_log_group.redis-slow-log-group.skip_destroy == false

  ### Test aws_cloudwatch_log_group engine resource ###
  assert {
    condition     = aws_cloudwatch_log_group.redis-engine-log-group.name == "/aws/elasticache/test-redis/test-environment/test-redisRedis/engine"
    error_message = "Invalid config for aws_cloudwatch_log_group name"
  }

  assert {
    condition     = aws_cloudwatch_log_group.redis-engine-log-group.retention_in_days == 7
    error_message = "Invalid config for aws_cloudwatch_log_group retention_in_days"
  }

  # Cannot test for the default on a plan
  # aws_cloudwatch_log_group.redis-engine-log-group.skip_destroy == false

  assert {
    condition     = jsonencode(aws_cloudwatch_log_group.redis-engine-log-group.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }
}

run "aws_cloudwatch_log_subscription_filter_unit_test" {
  command = plan

  ### Test aws_cloudwatch_log_subscription_filter engine resource ###
  assert {
    condition     = aws_cloudwatch_log_subscription_filter.redis-subscription-filter-engine.name == "/aws/elasticache/test-application/test-environment/test-redis/engine"
    error_message = "Invalid config for aws_cloudwatch_log_subscription_filter name"
  }

  assert {
    condition     = aws_cloudwatch_log_subscription_filter.redis-subscription-filter-engine.destination_arn == "arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_dev"
    error_message = "Invalid config for aws_cloudwatch_log_subscription_filter destination_arn"
  }

  # Cannot test for the default on a plan
  # aws_cloudwatch_log_subscription_filter.redis-subscription-filter-engine.distribution == "ByLogStream"

  assert {
    condition     = aws_cloudwatch_log_subscription_filter.redis-subscription-filter-engine.role_arn == "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"
    error_message = "Invalid config for aws_cloudwatch_log_subscription_filter role_arn"
  }

  ### Test aws_cloudwatch_log_subscription_filter slow resource ###
  assert {
    condition     = aws_cloudwatch_log_subscription_filter.redis-subscription-filter-slow.name == "/aws/elasticache/test-application/test-environment/test-redis/slow"
    error_message = "Invalid config for aws_cloudwatch_log_subscription_filter name"
  }

  assert {
    condition     = aws_cloudwatch_log_subscription_filter.redis-subscription-filter-slow.destination_arn == "arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_dev"
    error_message = "Invalid config for aws_cloudwatch_log_subscription_filter destination_arn"
  }

  # Cannot test for the default on a plan
  # aws_cloudwatch_log_subscription_filter.redis-subscription-filter-slow.distribution == "ByLogStream"

  assert {
    condition     = aws_cloudwatch_log_subscription_filter.redis-subscription-filter-slow.role_arn == "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"
    error_message = "Invalid config for aws_cloudwatch_log_subscription_filter role_arn"
  }
}

run "aws_cloudwatch_log_subscription_filter_destination_prod_unit_test" {
  command = plan

  variables {
    environment = "prod"
  }

  assert {
    condition     = aws_cloudwatch_log_subscription_filter.redis-subscription-filter-engine.destination_arn == "arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_prod"
    error_message = "Invalid config for aws_cloudwatch_log_subscription_filter destination_arn"
  }

  assert {
    condition     = aws_cloudwatch_log_subscription_filter.redis-subscription-filter-slow.destination_arn == "arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_prod"
    error_message = "Invalid config for aws_cloudwatch_log_subscription_filter destination_arn"
  }
}

run "test_create_conduit_iam_role" {
  command = plan

  assert {
    condition     = aws_iam_role.conduit_ecs_task_role.name == "test-redis-test-application-test-environment-conduitEcsTask"
    error_message = "Should be: test-redis-test-application-test-environment-conduitEcsTask"
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
    condition     = aws_iam_role_policy.kms_access_for_conduit_ecs_task.role == "test-redis-test-application-test-environment-conduitEcsTask"
    error_message = "Should be: 'test-redis-test-application-test-environment-conduitEcsTask'"
  }
}
