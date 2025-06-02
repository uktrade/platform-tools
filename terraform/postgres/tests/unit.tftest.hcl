mock_provider "aws" {}

override_data {
  target = data.external.codestar_connections

  values = {
    result = {
      ConnectionArn = "ConnectionArn"
    }
  }
}

override_data {
  target = data.aws_caller_identity.current
  values = {
    account_id = "001122334455"
  }
}

override_data {
  target = data.aws_security_group.rds-endpoint
  values = {
    name = "sandbox-postgres-rds-endpoint-sg"
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
    ids = ["subnet-000111222aaabbb01"]
  }
}

override_data {
  target = data.aws_ssm_parameter.log-destination-arn
  values = {
    value = "{\"prod\":\"arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_prod\", \"dev\":\"arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_dev\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.lambda-assume-role-policy
  values = {
    json = "{\"Sid\": \"AllowLambdaAssumeRole\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.enhanced-monitoring
  values = {
    json = "{\"Sid\": \"AllowEnhancedMonitoringAssumeRole\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.lambda-execution-policy
  values = {
    json = "{\"Sid\": \"LambdaExecutionPolicy\"}"
  }
}

override_data {
  target = module.database-dump[0].data.aws_iam_policy_document.assume_ecs_task_role
  values = {
    json = "{\"Sid\": \"AllowECSAssumeRole\"}"
  }
}

override_data {
  target = module.database-dump[0].data.aws_iam_policy_document.allow_task_creation
  values = {
    json = "{\"Sid\": \"AllowPullFromEcr\"}"
  }
}

override_data {
  target = module.database-load[0].data.aws_iam_policy_document.assume_ecs_task_role
  values = {
    json = "{\"Sid\": \"AllowECSAssumeRole\"}"
  }
}

override_data {
  target = module.database-load[0].data.aws_iam_policy_document.allow_task_creation
  values = {
    json = "{\"Sid\": \"AllowPullFromEcr\"}"
  }
}

override_data {
  target = module.database-load[0].data.aws_iam_policy_document.data_load
  values = {
    json = "{\"Sid\": \"AllowReadFromS3\"}"
  }
}

override_data {
  target = module.database-load[0].data.aws_iam_policy_document.pipeline_access
  values = {
    json = "{\"Sid\": \"AllowPipelineAccess\"}"
  }
}

override_data {
  target = module.database-copy-pipeline[0].data.aws_iam_policy_document.assume_codepipeline_role
  values = {
    json = "{\"Sid\": \"AssumeCodePipeline\"}"
  }
}

override_data {
  target = module.database-copy-pipeline[0].data.aws_iam_policy_document.access_artifact_store
  values = {
    json = "{\"Sid\": \"AccessArtifactStore\"}"
  }
}

override_data {
  target = module.database-copy-pipeline[0].data.aws_iam_policy_document.assume_codebuild_role
  values = {
    json = "{\"Sid\": \"AssumeCodeBuild\"}"
  }
}

override_data {
  target = module.database-copy-pipeline[0].data.aws_iam_policy_document.ssm_access
  values = {
    json = "{\"Sid\": \"SSMAccess\"}"
  }
}

override_data {
  target = module.database-copy-pipeline[0].data.aws_iam_policy_document.assume_account_role
  values = {
    json = "{\"Sid\": \"AllowAssumeAccountRole\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.assume_ecstask_role
  values = {
    json = <<EOT
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      }
    }
  ]
}
EOT
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

variables {
  application = "test-application"
  environment = "test-env"
  name        = "test-name"
  vpc_name    = "sandbox-postgres"
  config = {
    version             = 14,
    deletion_protection = true,
    multi_az            = false,
    database_copy = [
      {
        from = "test-env"
        to   = "other-env"
      }
    ]
  }
  env_config = {
    "*" = {
      accounts = {
        deploy = {
          name = "sandbox"
          id   = "000123456789"
        }
      }
    },
    "test-env"  = null,
    "other-env" = null
  }
}


run "aws_security_group_unit_test" {
  command = plan

  assert {
    condition     = aws_security_group.default.name == "test-application-test-env-test-name"
    error_message = "Invalid name for aws_security_group.default"
  }

  # Cannot test for the default on a plan
  # aws_security_group.default.revoke_rules_on_delete == false

  assert {
    condition     = aws_security_group.default.tags.application == "test-application"
    error_message = "Invalid tags for aws_security_group.default application"
  }

  assert {
    condition     = aws_security_group.default.tags.environment == "test-env"
    error_message = "Invalid tags for aws_security_group.default copilot-environment"
  }

  assert {
    condition     = aws_security_group.default.tags.copilot-application == "test-application"
    error_message = "Invalid tags for aws_security_group.default application"
  }

  assert {
    condition     = aws_security_group.default.tags.copilot-environment == "test-env"
    error_message = "Invalid tags for aws_security_group.default copilot-environment"
  }

  assert {
    condition     = aws_security_group.default.tags.managed-by == "DBT Platform - Terraform"
    error_message = "Invalid tags for aws_security_group.default managed-by"
  }
}


run "aws_db_parameter_group_unit_test" {
  command = plan

  assert {
    condition     = aws_db_parameter_group.default.name == "test-application-test-env-test-name-postgres14"
    error_message = "Invalid name for aws_db_parameter_group.default"
  }

  assert {
    condition     = aws_db_parameter_group.default.family == "postgres14"
    error_message = "Invalid family for aws_db_parameter_group.default"
  }

  assert {
    condition     = [for el in aws_db_parameter_group.default.parameter : el.value if el.name == "client_encoding"][0] == "utf8"
    error_message = "Invalid value for for aws_db_parameter_group.default client_encoding parameter"
  }

  assert {
    condition     = [for el in aws_db_parameter_group.default.parameter : el.value if el.name == "log_statement"][0] == "ddl"
    error_message = "Invalid value for for aws_db_parameter_group.default log_statement parameter"
  }

  assert {
    condition     = [for el in aws_db_parameter_group.default.parameter : el.value if el.name == "log_statement_sample_rate"][0] == "1.0"
    error_message = "Invalid value for for aws_db_parameter_group.default log_statement_sample_rate parameter"
  }
}


run "aws_db_subnet_group_unit_test" {
  command = plan

  assert {
    condition     = aws_db_subnet_group.default.name == "test-application-test-env-test-name"
    error_message = "Invalid name for aws_db_subnet_group.default"
  }

  assert {
    condition     = length(aws_db_subnet_group.default.subnet_ids) == 1
    error_message = "Should be: 1"
  }
}

run "aws_kms_key_unit_test" {
  command = plan

  assert {
    condition     = aws_kms_key.default.description == "test-application-test-env-test-name KMS key"
    error_message = "Invalid description for aws_kms_key.default"
  }

  # Cannot test for the default on a plan
  # aws_kms_key.default.is_enabled == true

  # Cannot test for the default on a plan
  # aws_kms_key.default.bypass_policy_lockout_safety_check == false

  assert {
    condition     = aws_kms_key.default.enable_key_rotation == true
    error_message = "Should be: true"
  }

  # Cannot test for the default on a plan
  # aws_kms_key.default.key_usage == "ENCRYPT_DECRYPT"

  # Cannot test for the default on a plan
  # aws_kms_key.default.customer_master_key_spec == "SYMMETRIC_DEFAULT"
}

run "aws_db_instance_unit_test" {
  command = plan

  # Test aws_db_instance.default resource version
  assert {
    condition     = aws_db_instance.default.db_name == "main"
    error_message = "Invalid db_name for aws_db_instance.default"
  }

  assert {
    condition     = aws_db_instance.default.db_subnet_group_name == "test-application-test-env-test-name"
    error_message = "Invalid db_subnet_group_name for aws_db_instance.default"
  }

  assert {
    condition     = aws_db_instance.default.engine == "postgres"
    error_message = "Should be: postgres"
  }

  assert {
    condition     = aws_db_instance.default.engine_version == "14"
    error_message = "Should be: 14"
  }

  assert {
    condition     = aws_db_instance.default.username == "postgres"
    error_message = "Should be: postgres"
  }

  # Test aws_db_instance.default resource storage
  assert {
    condition     = aws_db_instance.default.storage_encrypted == true
    error_message = "Should be: true"
  }

  assert {
    condition     = aws_db_instance.default.publicly_accessible == false
    error_message = "Should be: false"
  }

  assert {
    condition     = aws_db_instance.default.iam_database_authentication_enabled == false
    error_message = "Should be: false"
  }

  assert {
    condition     = aws_db_instance.default.multi_az == false
    error_message = "Should be: false"
  }

  assert {
    condition     = aws_db_instance.default.backup_retention_period == 7
    error_message = "Should be: 7"
  }

  assert {
    condition     = aws_db_instance.default.backup_window == "07:00-09:00"
    error_message = "Should be: 07:00-09:00"
  }

  assert {
    condition     = aws_db_instance.default.allocated_storage == 100
    error_message = "Should be: 100"
  }

  assert {
    condition     = aws_db_instance.default.manage_master_user_password == true
    error_message = "Should be: true"
  }

  assert {
    condition     = aws_db_instance.default.copy_tags_to_snapshot == true
    error_message = "Should be: true"
  }

  assert {
    condition     = aws_db_instance.default.deletion_protection == true
    error_message = "Should be: true"
  }

  # Test aws_db_instance.default resource monitoring
  assert {
    condition     = aws_db_instance.default.performance_insights_enabled == true
    error_message = "Should be: true"
  }

  assert {
    condition     = aws_db_instance.default.performance_insights_retention_period == 7
    error_message = "Should be: 7"
  }

  assert {
    condition     = aws_db_instance.default.monitoring_interval == 15
    error_message = "Should be: 15"
  }

  # Test aws_db_instance.default resource upgrades
  assert {
    condition     = aws_db_instance.default.allow_major_version_upgrade == true
    error_message = "Should be: true"
  }

  assert {
    condition     = aws_db_instance.default.apply_immediately == false
    error_message = "Should be: false"
  }

  assert {
    condition     = aws_db_instance.default.auto_minor_version_upgrade == true
    error_message = "Should be: true"
  }

  assert {
    condition     = aws_db_instance.default.maintenance_window == "Mon:00:00-Mon:03:00"
    error_message = "Should be: Mon:00:00-Mon:03:00"
  }

  assert {
    condition     = aws_db_instance.default.storage_type == "gp3"
    error_message = "Should be: gp3"
  }

  assert {
    condition     = aws_db_instance.default.backup_retention_period == 7
    error_message = "Should be: 7"
  }

  # aws_db_instance.default.iops cannot be tested on a plan

  assert {
    condition     = length(module.database-dump) == 1
    error_message = "database-dump module should be created"
  }

  assert {
    condition     = length(module.database-load) == 0
    error_message = "database-load module should not be created"
  }
}

run "aws_db_instance_unit_test_database_dump_created" {
  command = plan

  variables {
    config = {
      version = 14,
      database_copy = [
        {
          from = "test-env"
          to   = "other-env"
        }
      ]
    }
  }

  assert {
    condition     = length(module.database-dump) == 1
    error_message = "database-dump module should be created"
  }

  assert {
    condition     = length(module.database-load) == 0
    error_message = "database-load module should not be created"
  }
}

run "aws_db_instance_unit_test_database_dump_multiple_source" {
  command = plan

  variables {
    config = {
      version = 14,
      database_copy = [
        {
          from = "test-env"
          to   = "other-env"
        },
        {
          from = "test-env"
          to   = "other-env-2"
        }
      ]
    }
    env_config = {
      "*" = {
        accounts = {
          deploy = {
            name = "sandbox"
            id   = "000123456789"
          }
        }
      },
      "test-env"  = null,
      "other-env" = null,
      "other-env-2" = {
        accounts = {
          deploy = {
            name = "prod"
            id   = "123456789000"
          }
        }
      }
    }
  }

  assert {
    condition     = length(module.database-dump) == 1
    error_message = "One database-dump module should be created"
  }

  assert {
    condition     = length(local.data_dump_tasks) == 2
    error_message = "There should be 2 database dump tasks"
  }

  assert {
    condition     = length(module.database-load) == 0
    error_message = "database-load module should not be created"
  }
}

run "aws_db_instance_unit_test_database_dump_not_created_if_to_env_is_prod" {
  command = plan

  variables {
    config = {
      version = 14,
      database_copy = [
        {
          from = "test-env"
          to   = "some-prod-environment"
        }
      ]
    }
  }

  assert {
    condition     = length(module.database-dump) == 0
    error_message = "database-dump module should not be created"
  }

  assert {
    condition     = length(module.database-load) == 0
    error_message = "database-load module should not be created"
  }
}

run "aws_db_instance_unit_test_database_load_created" {
  command = plan

  variables {
    config = {
      version = 14,
      database_copy = [
        {
          from = "other-env"
          to   = "test-env"
        }
      ]
    }
  }

  assert {
    condition     = length(module.database-dump) == 0
    error_message = "database-dump module should not be created"
  }

  assert {
    condition     = length(module.database-load) == 1
    error_message = "database-load module should be created"
  }
}

run "aws_db_instance_unit_test_database_load_not_created_if_to_env_is_prod" {
  command = plan

  variables {
    config = {
      version = 14,
      database_copy = [
        {
          from = "other-env"
          to   = "test-prod-environment"
        }
      ]
    }
  }

  assert {
    condition     = length(module.database-dump) == 0
    error_message = "database-dump module should not be created"
  }

  assert {
    condition     = length(module.database-load) == 0
    error_message = "database-load module should not be created"
  }
}

run "aws_db_instance_unit_test_set_to_non_defaults" {
  command = plan

  variables {
    config = {
      version               = 14,
      deletion_protection   = false,
      multi_az              = true,
      skip_final_snapshot   = true,
      volume_size           = 20,
      iops                  = 3000,
      instance              = "db.t3.small",
      storage_type          = "io2"
      backup_retention_days = 35
    }
  }

  # Test aws_db_instance.default resource version
  assert {
    condition     = aws_db_instance.default.deletion_protection == false
    error_message = "Should be: false"
  }

  assert {
    condition     = aws_db_instance.default.multi_az == true
    error_message = "Should be: true"
  }

  assert {
    condition     = aws_db_instance.default.skip_final_snapshot == true
    error_message = "Should be: true"
  }

  assert {
    condition     = aws_db_instance.default.allocated_storage == 20
    error_message = "Should be: 20"
  }

  assert {
    condition     = aws_db_instance.default.iops == 3000
    error_message = "Should be: 20"
  }

  assert {
    condition     = aws_db_instance.default.instance_class == "db.t3.small"
    error_message = "Should be: db.t3.small"
  }

  assert {
    condition     = aws_db_instance.default.storage_type == "io2"
    error_message = "Should be: io2"
  }

  assert {
    condition     = aws_db_instance.default.backup_retention_period == 35
    error_message = "Should be: 35"
  }
}

run "aws_iam_role_unit_test" {
  command = plan

  # Test aws_iam_role.enhanced-monitoring resource
  assert {
    condition     = aws_iam_role.enhanced-monitoring.name_prefix == "rds-enhanced-monitoring-"
    error_message = "Invalid name_prefix for aws_iam_role.enhanced-monitoring"
  }

  # Cannot test for the default on a plan
  # aws_iam_role.enhanced-monitoring.max_session_duration == 3600

  # Check that the correct aws_iam_policy_document is used from the mocked data json
  assert {
    condition     = aws_iam_role.enhanced-monitoring.assume_role_policy == "{\"Sid\": \"AllowEnhancedMonitoringAssumeRole\"}"
    error_message = "Should be: {\"Sid\": \"AllowEnhancedMonitoringAssumeRole\"}"
  }

  # Check the contents of the policy document
  assert {
    condition     = contains(data.aws_iam_policy_document.enhanced-monitoring.statement[0].actions, "sts:AssumeRole")
    error_message = "Should be: sts:AssumeRole"
  }
  assert {
    condition     = data.aws_iam_policy_document.enhanced-monitoring.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = [
      for el in data.aws_iam_policy_document.enhanced-monitoring.statement[0].principals :
      true if el.type == "Service" && [
        for identifier in el.identifiers : true if identifier == "monitoring.rds.amazonaws.com"
      ][0] == true
    ][0] == true
    error_message = "Should be: Service monitoring.rds.amazonaws.com"
  }

  # Cannot test for the default on a plan
  # jsondecode(aws_iam_role.enhanced-monitoring.assume_role_policy).Version == "2012-10-17"

  # Test aws_iam_role_policy_attachment.enhanced-monitoring resource
  assert {
    condition     = aws_iam_role_policy_attachment.enhanced-monitoring.policy_arn == "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
    error_message = "Invalid policy_arn for aws_iam_role_policy_attachment.enhanced-monitoring"
  }

  # Test aws_iam_role.lambda-execution-role resource
  assert {
    condition     = aws_iam_role.lambda-execution-role.name == "test-application-test-env-test-name-lambda-role"
    error_message = "Invalid name for aws_iam_role.lambda-execution-role"
  }

  # Cannot test for the default on a plan
  # aws_iam_role.lambda-execution-role.max_session_duration == 3600

  # Check that the correct aws_iam_policy_document is used from the mocked data json
  assert {
    condition     = aws_iam_role.lambda-execution-role.assume_role_policy == "{\"Sid\": \"AllowLambdaAssumeRole\"}"
    error_message = "Should be: {\"Sid\": \"AllowLambdaAssumeRole\"}"
  }

  # Check lambda execution role policy
  assert {
    condition     = aws_iam_role_policy.lambda-execution-role-policy.name == "test-application-test-env-test-name-execution-policy"
    error_message = "Should be: 'test-application-test-env-test-name-execution-policy'"
  }
  assert {
    condition     = aws_iam_role_policy.lambda-execution-role-policy.role == "test-application-test-env-test-name-lambda-role"
    error_message = "Should be: 'test-application-test-env-test-name-lambda-role'"
  }
  assert {
    condition     = aws_iam_role_policy.lambda-execution-role-policy.policy == "{\"Sid\": \"LambdaExecutionPolicy\"}"
    error_message = "Unexpected policy"
  }

  # Check the contents of the policy document
  assert {
    condition     = contains(data.aws_iam_policy_document.lambda-assume-role-policy.statement[0].actions, "sts:AssumeRole")
    error_message = "Should be: sts:AssumeRole"
  }

  assert {
    condition = [
      for el in data.aws_iam_policy_document.lambda-assume-role-policy.statement[0].principals :
      true if el.type == "Service" && [
        for identifier in el.identifiers : true if identifier == "lambda.amazonaws.com"
      ][0] == true
    ][0] == true
    error_message = "Should be: Service lambda.amazonaws.com"
  }
}

run "aws_cloudwatch_log_rds_subscription_filter_unit_test" {
  command = plan

  assert {
    condition     = aws_cloudwatch_log_subscription_filter.rds.name == "/aws/rds/instance/test-application/test-env/test-name/postgresql"
    error_message = "Invalid name for aws_cloudwatch_log_subscription_filter.rds"
  }

  assert {
    condition     = endswith(aws_cloudwatch_log_subscription_filter.rds.role_arn, ":role/CWLtoSubscriptionFilterRole") == true
    error_message = "Invalid role_arn for aws_cloudwatch_log_subscription_filter.rds"
  }

  # Cannot test for the default on a plan
  # aws_cloudwatch_log_subscription_filter.rds.distribution == "ByLogStream"

  assert {
    condition     = aws_cloudwatch_log_subscription_filter.rds.destination_arn == "arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_dev"
    error_message = "Should be: arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_dev"
  }
}

run "aws_lambda_function_unit_test" {
  command = plan

  assert {
    condition     = aws_lambda_function.lambda.filename == "./manage_users.zip"
    error_message = "Should be: ./manage_users.zip"
  }

  assert {
    condition     = aws_lambda_function.lambda.function_name == "test-application-test-env-test-name-rds-create-user"
    error_message = "Should be: test-application-test-env-test-name-rds-create-user"
  }

  assert {
    condition     = aws_lambda_function.lambda.handler == "manage_users.handler"
    error_message = "Should be: manage_users.handler"
  }

  assert {
    condition     = aws_lambda_function.lambda.runtime == "python3.11"
    error_message = "Should be: python3.11"
  }

  assert {
    condition     = aws_lambda_function.lambda.memory_size == 128
    error_message = "Should be: 128"
  }

  assert {
    condition     = aws_lambda_function.lambda.timeout == 10
    error_message = "Should be: 10"
  }

  assert {
    condition     = length(aws_lambda_function.lambda.layers) == 1
    error_message = "Should be: 1"
  }

  assert {
    condition     = endswith(aws_lambda_function.lambda.layers[0], ":layer:python-postgres:1") == true
    error_message = "Should be: end with layer:python-postgres:1"
  }

  # Cannot test for the default on a plan
  # [for el in aws_lambda_function.lambda.vpc_config : true if el.ipv6_allowed_for_dual_stack == false][0] == true
}

run "aws_lambda_invocation_unit_test" {
  command = plan

  # Test aws_lambda_invocation.create-application-user resource
  assert {
    condition     = aws_lambda_invocation.create-application-user.function_name == "test-application-test-env-test-name-rds-create-user"
    error_message = "Should be: test-application-test-env-test-name-rds-create-user"
  }

  # Cannot test for the default on a plan
  # aws_lambda_invocation.create-application-user.lifecycle_scope == "CREATE_ONLY"

  # Cannot test for the default on a plan
  # aws_lambda_invocation.create-application-user.qualifier == "$LATEST"

  # Cannot test for the default on a plan
  # aws_lambda_invocation.create-application-user.terraform_key == "tf"

  # Test aws_lambda_invocation.create-readonly-user resource
  assert {
    condition     = aws_lambda_invocation.create-readonly-user.function_name == "test-application-test-env-test-name-rds-create-user"
    error_message = "Should be: test-application-test-env-test-name-rds-create-user"
  }

  # Cannot test for the default on a plan
  # aws_lambda_invocation.create-readonly-user.lifecycle_scope == "CREATE_ONLY"

  # Cannot test for the default on a plan
  # aws_lambda_invocation.create-readonly-user.qualifier == "$LATEST"

  # Cannot test for the default on a plan
  # aws_lambda_invocation.create-readonly-user.terraform_key == "tf"

  assert {
    condition     = aws_lambda_function.lambda.reserved_concurrent_executions == -1
    error_message = "Should be: -1"
  }
}

run "aws_ssm_parameter_master_secret_arn_unit_test" {
  command = plan

  assert {
    condition     = aws_ssm_parameter.master-secret-arn.name == "/copilot/test-application/test-env/secrets/TEST_NAME_RDS_MASTER_ARN"
    error_message = "Should be: /copilot/test-application/test-env/secrets/TEST_NAME_RDS_MASTER_ARN"
  }

  assert {
    condition     = aws_ssm_parameter.master-secret-arn.type == "SecureString"
    error_message = "Should be: SecureString"
  }
}

run "aws_db_instance_database_copy_pipeline" {
  command = plan

  variables {
    config = {
      version = 14,
      database_copy = [
        {
          from = "test-env"
          to   = "other-env"
        },
        {
          from     = "other-env"
          to       = "test-env"
          pipeline = {}
        }
      ]
    }
  }

  assert {
    condition     = length(module.database-load) == 1
    error_message = "database-load module should be created"
  }

  assert {
    condition     = length(module.database-copy-pipeline) == 1
    error_message = "database-copy-pipeline module should be created"
  }
}

run "aws_db_prod_account_environment_parameter" {
  command = plan

  variables {
    config = {
      version = 14,
      database_copy = [
        {
          from = "test-env"
          to   = "other-env"
        },
        {
          from = "other-env"
          to   = "test-env"
        }
      ]
    }
    env_config = {
      "*" = {
        accounts = {
          deploy = {
            name = "sandbox"
            id   = "000123456789"
          }
        }
      },
      "other-env" = null,
      "test-env" = {
        accounts = {
          deploy = {
            name = "prod"
            id   = "123456789000"
          }
        }
      }
    }
  }

  assert {
    condition     = length(aws_ssm_parameter.environment_config) == 1
    error_message = "Should be: 1"
  }
  assert {
    condition     = aws_ssm_parameter.environment_config["test-env"].name == "/copilot/applications/test-application/environments/test-env"
    error_message = "Should be: /copilot/applications/test-application/environments/test-env"
  }
  assert {
    condition     = aws_ssm_parameter.environment_config["test-env"].type == "String"
    error_message = "Should be: String"
  }
  assert {
    condition     = jsondecode(aws_ssm_parameter.environment_config["test-env"].value).app == "test-application"
    error_message = "Should be: test-application"
  }
  assert {
    condition     = jsondecode(aws_ssm_parameter.environment_config["test-env"].value).name == "test-env"
    error_message = "Should be: test-env"
  }
  assert {
    condition     = jsondecode(aws_ssm_parameter.environment_config["test-env"].value).region == "eu-west-2"
    error_message = "Should be: eu-west-2"
  }
  assert {
    condition     = jsondecode(aws_ssm_parameter.environment_config["test-env"].value).accountID == "123456789000"
    error_message = "Should be: 123456789000"
  }
}
