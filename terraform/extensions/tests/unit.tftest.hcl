variables {
  args = {
    application = "test-application",
    services = {
      "test-s3" : {
        "type" : "s3",
        "services" : ["web"],
        "environments" : {
          "test-env" : {
            "bucket_name" : "extensions-test-bucket",
            "versioning" : false
          },
          "other-env" : {
            "bucket_name" : "other-env-extensions-test-bucket",
            "versioning" : false
          }
        }
      },
      "test-opensearch" : {
        "type" : "opensearch",
        "name" : "test-small",
        "environments" : {
          "test-env" : {
            "engine" : "2.11",
            "plan" : "small",
            "volume_size" : 512
          },
          "other-env" : {
            "engine" : "2.11",
            "plan" : "small",
            "volume_size" : 512
          }
        }
      }
    },
    env_config = {
      "*" = {
        accounts = {
          deploy = {
            name = "sandbox"
            id   = "000123456789"
          }
          dns = {
            name = "dev"
            id   = "123456"
          }
        }
        vpc : "test-vpc"
      },
      "test-env" = {
        accounts = {
          deploy = {
            name = "sandbox"
            id   = "000123456789"
          }
          dns = {
            name = "dev"
            id   = "123456"
          }
        }
        vpc : "test-vpc"
        service-deployment-mode : "doesn't matter"
      }
    }
  }
  environment = "test-env"
}

mock_provider "aws" {
  alias = "prod"
}

mock_provider "aws" {
  alias = "domain"
}

mock_provider "aws" {
  alias = "domain-cdn"
}

mock_provider "aws" {}

mock_provider "datadog" {
  alias = "ddog"
}

override_data {
  target = module.opensearch["test-opensearch"].data.aws_caller_identity.current
  values = {
    account_id = "001122334455"
  }
}

override_data {
  target = module.opensearch["test-opensearch"].data.aws_iam_policy_document.assume_ecstask_role
  values = {
    json = "{\"Sid\": \"AllowAssumeECSTaskRole\"}"
  }
}

override_data {
  target = module.opensearch["test-opensearch"].data.aws_ssm_parameter.log-destination-arn
  values = {
    value = "{\"dev\":\"arn:aws:logs:eu-west-2:763451185160:log-group:/copilot/tools/central_log_groups_dev\",\"prod\":\"arn:aws:logs:eu-west-2:763451185160:log-group:/copilot/tools/central_log_groups_prod\"}"
  }
}

override_data {
  target = module.opensearch["test-opensearch"].data.aws_vpc.vpc
  values = {
    id         = "vpc-00112233aabbccdef"
    cidr_block = "10.0.0.0/16"
  }
}

override_data {
  target = module.opensearch["test-opensearch"].data.aws_subnets.private-subnets
  values = {
    ids = ["subnet-000111222aaabbb01", "subnet-000111222aaabbb02", ]
  }
}

override_data {
  target = module.opensearch["test-opensearch"].data.aws_iam_policy_document.conduit_task_role_access
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

override_data {
  target = module.elasticache-redis["test-redis"].data.aws_ssm_parameter.log-destination-arn
  values = {
    value = "{\"dev\":\"arn:aws:logs:eu-west-2:763451185160:log-group:/copilot/tools/central_log_groups_dev\"}"
  }
}

override_data {
  target = module.elasticache-redis["test-redis"].data.aws_vpc.vpc
  values = {
    id         = "vpc-00112233aabbccdef"
    cidr_block = "10.0.0.0/16"
  }
}

override_data {
  target = module.elasticache-redis["test-redis"].data.aws_iam_policy_document.assume_ecstask_role
  values = {
    json = "{\"Version\": \"2012-10-17\", \"Statement\": [{\"Effect\": \"Allow\", \"Principal\": {\"Service\": \"ecs-tasks.amazonaws.com\"}, \"Action\": \"sts:AssumeRole\"}]}"
  }
}

override_data {
  target = module.elasticache-redis["test-redis"].data.aws_caller_identity.current
  values = {
    account_id = "123456789012"
  }
}

override_data {
  target = module.elasticache-redis["test-redis"].data.aws_iam_policy_document.conduit_task_role_access
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

override_data {
  target = data.aws_iam_policy_document.cloudformation_access
  values = {
    json = "{\"Sid\": \"CloudFormationAccess\"}"
  }
}

override_data {
  target = data.aws_ssm_parameter.log_destination_arn
  values = {
    value = "{\"dev\":\"arn:aws:logs:eu-west-2:001122334455:log-group:/central/dev\",\"prod\":\"arn:aws:logs:eu-west-2:001122334455:log-group:/central/prod\"}"
  }
}

override_data {
  target = module.alb["test-alb"].data.aws_vpc.vpc
  values = {
    id         = "vpc-00112233aabbccdef"
    cidr_block = "10.0.0.0/16"
    tags = {
      Name = "test"
    }
  }
}

override_data {
  target = module.alb["test-alb"].data.aws_iam_policy_document.listener-rule-organiser-role-assume
  values = {
    json = "{\"Sid\": \"AllowAssumeECSTaskRole\"}"
  }
}

override_module {
  target = module.alb[0]
  outputs = {
    https_security_group_id = "security-group-id"
  }
}

run "aws_ssm_parameter_unit_test" {
  command = plan

  # Configuration
  assert {
    condition     = aws_ssm_parameter.addons.name == "/copilot/applications/test-application/environments/test-env/addons"
    error_message = "Invalid config for aws_ssm_parameter name"
  }
  assert {
    condition     = aws_ssm_parameter.addons.tier == "Intelligent-Tiering"
    error_message = "Intelligent-Tiering not enabled, parameters > 4096 characters will be rejected"
  }
  assert {
    condition     = aws_ssm_parameter.addons.type == "String"
    error_message = "Invalid config for aws_ssm_parameter type"
  }

  # Value only includes current environment
  assert {
    condition     = strcontains(aws_ssm_parameter.addons.value, "type")
    error_message = ""
  }
  assert {
    condition     = strcontains(aws_ssm_parameter.addons.value, "other-env") == false
    error_message = ""
  }

  # Tags
  assert {
    condition     = aws_ssm_parameter.addons.tags["application"] == "test-application"
    error_message = ""
  }
  assert {
    condition     = aws_ssm_parameter.addons.tags["copilot-application"] == "test-application"
    error_message = ""
  }
  assert {
    condition     = aws_ssm_parameter.addons.tags["environment"] == "test-env"
    error_message = ""
  }
  assert {
    condition     = aws_ssm_parameter.addons.tags["copilot-environment"] == "test-env"
    error_message = ""
  }
  assert {
    condition     = aws_ssm_parameter.addons.tags["managed-by"] == "DBT Platform - Terraform"
    error_message = ""
  }
}

run "s3_service_test" {
  command = plan

  assert {
    condition     = output.resolved_config.test-s3.bucket_name == "extensions-test-bucket"
    error_message = "Should be: extensions-test-bucket"
  }

  assert {
    condition     = output.resolved_config.test-s3.type == "s3"
    error_message = "Should be: s3"
  }

  assert {
    condition     = output.resolved_config.test-s3.versioning == false
    error_message = "Should be: false"
  }
}

run "opensearch_plan_small_service_test" {
  command = plan

  assert {
    condition     = output.resolved_config.test-opensearch.engine == "2.11"
    error_message = "Should be: 2.11"
  }

  assert {
    condition     = output.resolved_config.test-opensearch.instance == "t3.medium.search"
    error_message = "Should be: t3.medium.search"
  }

  assert {
    condition     = output.resolved_config.test-opensearch.instances == 1
    error_message = "Should be: 1"
  }

  assert {
    condition     = output.resolved_config.test-opensearch.enable_ha == false
    error_message = "Should be: false"
  }

  assert {
    condition     = output.resolved_config.test-opensearch.name == "test-small"
    error_message = "Should be: test-small"
  }

  assert {
    condition     = output.resolved_config.test-opensearch.type == "opensearch"
    error_message = "Should be: opensearch"
  }

  assert {
    condition     = output.resolved_config.test-opensearch.volume_size == 512
    error_message = "Should be: 512"
  }
}

run "opensearch_plan_medium_ha_service_test" {
  variables {
    args = {
      application = "test-application",
      services = {
        "test-opensearch" : {
          "type" : "opensearch",
          "name" : "test-medium-ha"
          "environments" : {
            "test-env" : {
              "engine" : "2.11",
              "plan" : "medium-ha"
            }
          }
        }
      },
      env_config = {
        "*" = {
          accounts = {
            deploy = {
              name = "sandbox"
              id   = "000123456789"
            }
            dns = {
              name = "dev"
              id   = "123456"
            }
          }
          vpc : "test-vpc"
        },
        "test-env" = {
          accounts = {
            deploy = {
              name = "sandbox"
              id   = "000123456789"
            }
            dns = {
              name = "dev"
              id   = "123456"
            }
          }
          vpc : "test-vpc"
          service-deployment-mode : "doesn't matter"
        }
      }
    }
    environment = "test-env"
  }

  command = plan

  assert {
    condition     = output.resolved_config.test-opensearch.engine == "2.11"
    error_message = "Should be: 2.11"
  }

  assert {
    condition     = output.resolved_config.test-opensearch.instance == "m6g.large.search"
    error_message = "Should be: m6g.large.search"
  }

  assert {
    condition     = output.resolved_config.test-opensearch.instances == 2
    error_message = "Should be: 2"
  }

  assert {
    condition     = output.resolved_config.test-opensearch.enable_ha == true
    error_message = "Should be: true"
  }

  assert {
    condition     = output.resolved_config.test-opensearch.name == "test-medium-ha"
    error_message = "Should be: test-medium-ha"
  }

  assert {
    condition     = output.resolved_config.test-opensearch.type == "opensearch"
    error_message = "Should be: opensearch"
  }

  assert {
    condition     = output.resolved_config.test-opensearch.volume_size == 512
    error_message = "Should be: 512"
  }
}

run "redis_plan_medium_service_test" {
  command = plan

  variables {
    args = {
      application = "test-application",
      services = {
        "test-redis" : {
          "type" : "redis",
          "name" : "test-medium",
          "environments" : {
            "test-env" : {
              "engine" : "7.1",
              "plan" : "medium"
            }
          }
        }
      },
      env_config = {
        "*" = {
          accounts = {
            deploy = {
              name = "sandbox"
              id   = "000123456789"
            }
            dns = {
              name = "dev"
              id   = "123456"
            }
          }
          vpc : "test-vpc"
        },
        "test-env" = {
          accounts = {
            deploy = {
              name = "sandbox"
              id   = "000123456789"
            }
            dns = {
              name = "dev"
              id   = "123456"
            }
          }
          vpc : "test-vpc"
          service-deployment-mode : "doesn't matter"
        }
      }
    }
    environment = "test-env"
  }

  assert {
    condition     = output.resolved_config.test-redis.engine == "7.1"
    error_message = "Should be: 7.1"
  }

  assert {
    condition     = output.resolved_config.test-redis.instance == "cache.m6g.large"
    error_message = "Should be: cache.m6g.large"
  }

  assert {
    condition     = output.resolved_config.test-redis.replicas == 0
    error_message = "Should be: 0 (single node)"
  }

  assert {
    condition     = output.resolved_config.test-redis.automatic_failover_enabled == false
    error_message = "Should be: false"
  }

  assert {
    condition     = output.resolved_config.test-redis.multi_az_enabled == false
    error_message = "Should be: false"
  }
}

run "redis_plan_medium_ha_service_test" {
  command = plan

  variables {
    args = {
      application = "test-application",
      services = {
        "test-redis" : {
          "type" : "redis",
          "name" : "test-medium-ha",
          "environments" : {
            "test-env" : {
              "engine" : "7.1",
              "plan" : "medium-ha"
            }
          }
        }
      },
      env_config = {
        "*" = {
          accounts = {
            deploy = {
              name = "sandbox"
              id   = "000123456789"
            }
            dns = {
              name = "dev"
              id   = "123456"
            }
          }
          vpc : "test-vpc"
        },
        "test-env" = {
          accounts = {
            deploy = {
              name = "sandbox"
              id   = "000123456789"
            }
            dns = {
              name = "dev"
              id   = "123456"
            }
          }
          vpc : "test-vpc"
          service-deployment-mode : "doesn't matter"
        }
      }
    }
    environment = "test-env"
  }

  assert {
    condition     = output.resolved_config.test-redis.engine == "7.1"
    error_message = "Should be: 7.1"
  }

  assert {
    condition     = output.resolved_config.test-redis.instance == "cache.m6g.large"
    error_message = "Should be: cache.m6g.large"
  }

  assert {
    condition     = output.resolved_config.test-redis.replicas == 2
    error_message = "Should be: 2 (highly available)"
  }

  assert {
    condition     = output.resolved_config.test-redis.automatic_failover_enabled == true
    error_message = "Should be: true"
  }

  assert {
    condition     = output.resolved_config.test-redis.multi_az_enabled == true
    error_message = "Should be: true"
  }
}


override_data {
  target = data.aws_iam_policy_document.assume_codebase_pipeline
  values = {
    json = "{\"Sid\": \"CodeBaseDeployAssume\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.ecr_access
  values = {
    json = "{\"Sid\": \"ECRAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.artifact_store_access
  values = {
    json = "{\"Sid\": \"ArtifactStoreAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.ecs_deploy_access
  values = {
    json = "{\"Sid\": \"ECSDeployAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.iam_access_for_codebase
  values = {
    json = "{\"Sid\": \"IAMAccessForCodebase\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.ecs_service_access_for_codebase
  values = {
    json = "{\"Sid\": \"ECSServiceAccessForCodebase\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.validate_platform_config_for_codebase
  values = {
    json = "{\"Sid\": \"ValidatePlatformConfigFoCodebase\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.state_kms_key_access
  values = {
    json = "{\"Sid\": \"stateKMSKeyAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.state_bucket_access
  values = {
    json = "{\"Sid\": \"stateBucketAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.state_lock_dynamo_db_access
  values = {
    json = "{\"Sid\": \"StateLockDynamoDBAccess\"}"
  }
}

run "codebase_deploy_iam_test" {
  command = plan

  variables {
    expected_tags = {
      application         = var.args.application
      environment         = var.environment
      managed-by          = "DBT Platform - Terraform"
      copilot-application = var.args.application
      copilot-environment = var.environment
    }
  }

  assert {
    condition     = aws_iam_role.codebase_pipeline_deploy.name == "test-application-test-env-codebase-pipeline-deploy"
    error_message = "Should be: 'test-application-test-env-codebase-pipeline-deploy'"
  }
  assert {
    condition     = aws_iam_role.codebase_pipeline_deploy.assume_role_policy == "{\"Sid\": \"CodeBaseDeployAssume\"}"
    error_message = "Should be: {\"Sid\": \"CodeBaseDeployAssume\"}"
  }
  assert {
    condition     = data.aws_iam_policy_document.assume_codebase_pipeline.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.assume_codebase_pipeline.statement[0].actions) == "sts:AssumeRole"
    error_message = "Should be: sts:AssumeRole"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.assume_codebase_pipeline.statement[0].principals).type == "AWS"
    error_message = "Should be: AWS"
  }
  assert {
    condition     = contains(one(data.aws_iam_policy_document.assume_codebase_pipeline.statement[0].principals).identifiers, "arn:aws:iam::000123456789:root")
    error_message = "Should contain: arn:aws:iam::000123456789:root"
  }
  assert {
    condition     = [for el in data.aws_iam_policy_document.assume_codebase_pipeline.statement[0].condition : el.test][0] == "ArnLike"
    error_message = "Should be: ArnLike"
  }
  assert {
    condition     = [for el in data.aws_iam_policy_document.assume_codebase_pipeline.statement[0].condition : el.variable][0] == "aws:PrincipalArn"
    error_message = "Should be: aws:PrincipalArn"
  }
  assert {
    condition = flatten([for el in data.aws_iam_policy_document.assume_codebase_pipeline.statement[0].condition : el.values][0]) == [
      "arn:aws:iam::000123456789:role/test-application-*-codebase-pipeline",
      "arn:aws:iam::000123456789:role/test-application-*-codebase-pipeline-*",
      "arn:aws:iam::000123456789:role/test-application-*-codebase-*"
    ]
    error_message = "Unexpected condition values"
  }
  assert {
    condition     = jsonencode(aws_iam_role.codebase_pipeline_deploy.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }
  assert {
    condition     = aws_iam_role_policy.ecr_access.name == "ecr-access"
    error_message = "Should be: 'ecr-access'"
  }
  assert {
    condition     = aws_iam_role_policy.ecr_access.role == "test-application-test-env-codebase-pipeline-deploy"
    error_message = "Should be: 'test-application-test-env-codebase-pipeline-deploy'"
  }
  assert {
    condition     = aws_iam_role_policy.ecr_access.policy == "{\"Sid\": \"ECRAccess\"}"
    error_message = "Should be: {\"Sid\": \"ECRAccess\"}"
  }
  assert {
    condition     = data.aws_iam_policy_document.ecr_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.ecr_access.statement[0].actions) == "ecr:DescribeImages"
    error_message = "Unexpected actions"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.ecr_access.statement[0].resources) == "arn:aws:ecr:${data.aws_region.current.region}:000123456789:repository/test-application/*"
    error_message = "Unexpected resources"
  }
  assert {
    condition     = aws_iam_role_policy.artifact_store_access.name == "artifact-store-access"
    error_message = "Should be: 'artifact-store-access'"
  }
  assert {
    condition     = aws_iam_role_policy.artifact_store_access.role == "test-application-test-env-codebase-pipeline-deploy"
    error_message = "Should be: 'test-application-test-env-codebase-pipeline-deploy'"
  }
  assert {
    condition     = aws_iam_role_policy.artifact_store_access.policy == "{\"Sid\": \"ArtifactStoreAccess\"}"
    error_message = "Should be: {\"Sid\": \"ArtifactStoreAccess\"}"
  }
  assert {
    condition     = data.aws_iam_policy_document.artifact_store_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.artifact_store_access.statement[0].actions == toset([
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:GetBucketVersioning",
      "s3:PutObjectAcl",
      "s3:PutObject",
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = data.aws_iam_policy_document.artifact_store_access.statement[0].resources == toset(["arn:aws:s3:::test-application-*-cb-arts", "arn:aws:s3:::test-application-*-cb-arts/*"])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.artifact_store_access.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.artifact_store_access.statement[1].actions == toset([
      "codebuild:BatchGetBuilds",
      "codebuild:StartBuild",
      "codebuild:StopBuild"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.artifact_store_access.statement[1].resources) == "*"
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.artifact_store_access.statement[2].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.artifact_store_access.statement[2].actions == toset([
      "kms:GenerateDataKey",
      "kms:Decrypt"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.artifact_store_access.statement[2].resources) == "arn:aws:kms:${data.aws_region.current.region}:000123456789:key/*"
    error_message = "Unexpected resources"
  }
  assert {
    condition     = aws_iam_role_policy.ecs_deploy_access.name == "ecs-deploy-access"
    error_message = "Should be: 'ecs-deploy-access'"
  }
  assert {
    condition     = aws_iam_role_policy.ecs_deploy_access.role == "test-application-test-env-codebase-pipeline-deploy"
    error_message = "Should be: 'test-application-test-env-codebase-pipeline-deploy'"
  }
  assert {
    condition     = aws_iam_role_policy.ecs_deploy_access.policy == "{\"Sid\": \"ECSDeployAccess\"}"
    error_message = "Should be: {\"Sid\": \"ECSDeployAccess\"}"
  }
  assert {
    condition     = data.aws_iam_policy_document.ecs_deploy_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.ecs_deploy_access.statement[0].actions == toset([
      "ecs:UpdateService",
      "ecs:DescribeServices",
      "ecs:TagResource",
      "ecs:ListServices"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.ecs_deploy_access.statement[0].resources == toset([
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:cluster/test-application-test-env",
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:service/test-application-test-env/*",
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:cluster/test-application-test-env-cluster",
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:service/test-application-test-env-cluster/*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.ecs_deploy_access.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.ecs_deploy_access.statement[1].actions == toset([
      "ecs:DescribeTasks",
      "ecs:TagResource"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.ecs_deploy_access.statement[1].resources == toset([
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:cluster/test-application-test-env",
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:task/test-application-test-env/*",
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:cluster/test-application-test-env-cluster",
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:task/test-application-test-env-cluster/*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.ecs_deploy_access.statement[2].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.ecs_deploy_access.statement[2].actions == toset([
      "ecs:RunTask",
      "ecs:TagResource"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.ecs_deploy_access.statement[2].resources) == "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:task-definition/test-application-test-env-*:*"
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.ecs_deploy_access.statement[3].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.ecs_deploy_access.statement[3].actions) == "ecs:ListTasks"
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.ecs_deploy_access.statement[3].resources == toset([
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:container-instance/test-application-test-env/*",
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:container-instance/test-application-test-env-cluster/*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.ecs_deploy_access.statement[4].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.ecs_deploy_access.statement[4].actions == toset([
      "ecs:DescribeTaskDefinition",
      "ecs:RegisterTaskDefinition"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.ecs_deploy_access.statement[4].resources) == "*"
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.ecs_deploy_access.statement[5].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.ecs_deploy_access.statement[5].actions) == "iam:PassRole"
    error_message = "Unexpected actions"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.ecs_deploy_access.statement[5].resources) == "*"
    error_message = "Unexpected resources"
  }
  assert {
    condition     = [for el in data.aws_iam_policy_document.ecs_deploy_access.statement[5].condition : el.test][0] == "StringLike"
    error_message = "Should be: StringLike"
  }
  assert {
    condition     = [for el in data.aws_iam_policy_document.ecs_deploy_access.statement[5].condition : one(el.values)][0] == "ecs-tasks.amazonaws.com"
    error_message = "Should be: ecs-tasks.amazonaws.com"
  }
  assert {
    condition     = [for el in data.aws_iam_policy_document.ecs_deploy_access.statement[5].condition : el.variable][0] == "iam:PassedToService"
    error_message = "Should be: iam:PassedToService"
  }
  assert {
    condition     = data.aws_iam_policy_document.ecs_deploy_access.statement[6].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.ecs_deploy_access.statement[6].actions == toset([
      "ecs:ListServiceDeployments"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.ecs_deploy_access.statement[6].resources == toset([
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:service/test-application-test-env/*",
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:service/test-application-test-env-cluster/*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = aws_iam_role_policy.cloudformation_access.name == "cloudformation-access"
    error_message = "Should be: 'cloudformation-access'"
  }
  assert {
    condition     = aws_iam_role_policy.cloudformation_access.role == "test-application-test-env-codebase-pipeline-deploy"
    error_message = "Should be: 'test-application-test-env-codebase-pipeline-deploy'"
  }
  assert {
    condition     = aws_iam_role_policy.cloudformation_access.policy == "{\"Sid\": \"CloudFormationAccess\"}"
    error_message = "Should be: {\"Sid\": \"CloudFormationAccess\"}"
  }
  assert {
    condition     = data.aws_iam_policy_document.cloudformation_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.cloudformation_access.statement[0].actions == toset([
      "cloudformation:GetTemplate"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.cloudformation_access.statement[0].resources == toset([
      "arn:aws:cloudformation:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:stack/test-application-test-env-*"
    ])
    error_message = "Unexpected resources"
  }
}

run "test_unrestricted_egress" {
  command = plan

  variables {
    args = {
      application = "test-application"
      services    = {}
      env_config = {
        "*" = {
          accounts = {
            deploy = {
              name = "sandbox"
              id   = "000123456789"
            }
            dns = {
              name = "dev"
              id   = "123456"
            }
          }
          vpc : "test-vpc"
        },
        "test-env" = {
          accounts = {
            deploy = {
              name = "sandbox"
              id   = "000123456789"
            }
            dns = {
              name = "dev"
              id   = "123456"
            }
          }
          vpc : "test-vpc"
          service-deployment-mode : "platform"
        }
      }
    }
    environment = "test-env"
  }

  assert {
    condition     = module.ecs_cluster[0].egress_rules == null
    error_message = "Expected module.ecs_cluster.egress_rules to be null"
  }

  assert {
    condition     = length(module.vpc_endpoints) == 0
    error_message = "Expected no instances of module.vpc_endpoints"
  }

  assert {
    condition     = !module.ecs_cluster[0].has_vpc_endpoints
    error_message = "Expected module.ecs_cluster[0].has_vpc_endpoints to be false"
  }
}

run "test_restricted_egress" {
  command = plan

  variables {
    args = {
      application = "test-application"
      services    = {}
      env_config = {
        "*" = {
          accounts = {
            deploy = {
              name = "sandbox"
              id   = "000123456789"
            }
            dns = {
              name = "dev"
              id   = "123456"
            }
          }
          vpc : "test-vpc"
        },
        "test-env" = {
          accounts = {
            deploy = {
              name = "sandbox"
              id   = "000123456789"
            }
            dns = {
              name = "dev"
              id   = "123456"
            }
          }
          vpc : "test-vpc"
          service-deployment-mode : "platform"
          network = {
            egress_rules = {
              myrule = {
                destination = { cidr_blocks = ["1.0.0.0/8"] }
                protocol    = "tcp"
                from_port   = 443
                to_port     = 443
              }
            }
          }
        }
      }
    }
    environment = "test-env"
  }

  assert {
    condition     = length(module.ecs_cluster[0].egress_rules) == 1
    error_message = "Expected module.ecs_cluster.egress_rules to match var.args.env_config.test-env.network.egress_rules"
  }

  assert {
    condition     = module.ecs_cluster[0].egress_rules["myrule"].destination.cidr_blocks == toset(["1.0.0.0/8"])
    error_message = "Expected module.ecs_cluster.egress_rules to match var.args.env_config.test-env.network.egress_rules"
  }

  assert {
    condition     = module.ecs_cluster[0].egress_rules["myrule"].protocol == "tcp"
    error_message = "Expected module.ecs_cluster.egress_rules to match var.args.env_config.test-env.network.egress_rules"
  }

  assert {
    condition     = length(module.vpc_endpoints) == 0
    error_message = "Expected no instances of module.vpc_endpoints"
  }

  assert {
    condition     = !module.ecs_cluster[0].has_vpc_endpoints
    error_message = "Expected module.ecs_cluster[0].has_vpc_endpoints to be false"
  }
}

run "test_create_vpc_endpoints" {
  command = plan

  variables {
    args = {
      application = "test-application"
      services    = {}
      env_config = {
        "*" = {
          accounts = {
            deploy = {
              name = "sandbox"
              id   = "000123456789"
            }
            dns = {
              name = "dev"
              id   = "123456"
            }
          }
          vpc : "test-vpc"
        },
        "test-env" = {
          accounts = {
            deploy = {
              name = "sandbox"
              id   = "000123456789"
            }
            dns = {
              name = "dev"
              id   = "123456"
            }
          }
          vpc : "test-vpc"
          service-deployment-mode : "platform"
          network = {
            vpc_endpoints = {
              ecr = {
                service_name = "com.amazonaws.eu-west-2.ecr.api"
              }
            }
          }
        }
      }
      environment = "test-env"
    }
  }

  assert {
    condition     = length(module.vpc_endpoints) == 1
    error_message = "Expected instance of module.vpc_endpoints"
  }

  assert {
    condition = module.vpc_endpoints[0].endpoint_definitions == tomap({
      ecr = {
        service_name = "com.amazonaws.eu-west-2.ecr.api"
      }
    })
    error_message = "vpc_endpoints service name is not as expected"
  }

  assert {
    condition     = module.ecs_cluster[0].has_vpc_endpoints
    error_message = "Expected module.ecs_cluster[0].has_vpc_endpoints to be true"
  }
}


run "test_cdn_without_managed_ingress" {
  command = plan

  variables {
    args = {
      application = "test-application"
      services = {
        test-alb = {
          type = "alb"
          environments = {
            test-env = {}
          }
        }
        test-alb = {
          type = "alb"
          environments = {
            test-env = {}
          }
        }
      }
      env_config = {
        "*" = {
          accounts = {
            deploy = {
              name = "sandbox"
              id   = "000123456789"
            }
            dns = {
              name = "dev"
              id   = "123456"
            }
          }
          vpc : "test-vpc"
        },
        "test-env" = {
          accounts = {
            deploy = {
              name = "sandbox"
              id   = "000123456789"
            }
            dns = {
              name = "dev"
              id   = "123456"
            }
          }
          vpc : "test-vpc"
          service-deployment-mode : "platform"
        }
      }
    }
    environment = "test-env"

  }

  assert {
    condition     = length(module.cdn) == 1
    error_message = "should be a single instance of module.cdn"
  }
}

run "test_cdn_with_managed_ingress" {
  command = plan

  variables {
    args = {
      application = "test-application"
      services = {
        test-alb = {
          type = "alb"
          environments = {
            "*" = {
              default_waf = "waf_test"
            }
            test-env = {
              managed_ingress = true
            }
            test1-env = {
              test_config = "123456"
            }
          }
        }
      }
      env_config = {
        "*" = {
          accounts = {
            deploy = {
              name = "sandbox"
              id   = "000123456789"
            }
            dns = {
              name = "dev"
              id   = "123456"
            }
          }
          vpc : "test-vpc"
        },
        "test-env" = {
          accounts = {
            deploy = {
              name = "sandbox"
              id   = "000123456789"
            }
            dns = {
              name = "dev"
              id   = "123456"
            }
          }
          vpc : "test-vpc"
          service-deployment-mode : "platform"
        }
      }
    }
    environment = "test-env"

  }

  assert {
    condition     = length(module.cdn) == 0
    error_message = "Should be no instance of module.cdn created"
  }

  assert {
    condition = local.extensions_with_default_and_environment_settings_merged.test-alb.default_waf == "waf_test"
    error_message = "Extension environment config for '*' environment expected at the top level" 
  }

  assert {
    condition = local.extensions_with_default_and_environment_settings_merged.test-alb.managed_ingress
    error_message = "Extension individual environment config for the selected environment expected at the top level"
  }

  assert {
    condition = !lookup(local.extensions_with_default_and_environment_settings_merged.test-alb, "test_config", false)
    error_message = "Extension individual environment config not expected at the top level for a different environment"
  }
}
