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
    condition     = strcontains(aws_ssm_parameter.addons.value, "test-env")
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
  target = module.pipeline_iam.data.aws_iam_policy_document.assume_codebase_pipeline
  values = {
    json = "{\"Sid\": \"CodeBaseDeployAssume\"}"
  }
}

override_data {
  target = module.pipeline_iam.data.aws_iam_policy_document.ecr_access
  values = {
    json = "{\"Sid\": \"ECRAccess\"}"
  }
}

override_data {
  target = module.pipeline_iam.data.aws_iam_policy_document.artifact_store_access
  values = {
    json = "{\"Sid\": \"ArtifactStoreAccess\"}"
  }
}

override_data {
  target = module.pipeline_iam.data.aws_iam_policy_document.ecs_deploy_access
  values = {
    json = "{\"Sid\": \"ECSDeployAccess\"}"
  }
}

override_data {
  target = module.pipeline_iam.data.aws_iam_policy_document.cloudformation_access
  values = {
    json = "{\"Sid\": \"CloudFormationAccess\"}"
  }
}

override_data {
  target = module.pipeline_iam.data.aws_iam_policy_document.assume_environment_pipeline
  values = {
    json = "{\"Sid\": \"AssumeEnvironmentPipeline\"}"
  }
}

override_data {
  target = module.pipeline_iam.data.aws_iam_policy_document.terraform_state_access
  values = {
    json = "{\"Sid\": \"TerraformStateAccess\"}"
  }
}

override_data {
  target = module.pipeline_iam.data.aws_iam_policy_document.vpc_access
  values = {
    json = "{\"Sid\": \"VPCAccess\"}"
  }
}

override_data {
  target = module.pipeline_iam.data.aws_iam_policy_document.alb_cdn_cert_access
  values = {
    json = "{\"Sid\": \"ALBAccess\"}"
  }
}

override_data {
  target = module.pipeline_iam.data.aws_iam_policy_document.ssm_access
  values = {
    json = "{\"Sid\": \"SSMAccess\"}"
  }
}

override_data {
  target = module.pipeline_iam.data.aws_iam_policy_document.logs_access
  values = {
    json = "{\"Sid\": \"LogsAccess\"}"
  }
}

override_data {
  target = module.pipeline_iam.data.aws_iam_policy_document.kms_key_access
  values = {
    json = "{\"Sid\": \"KMSAccess\"}"
  }
}

override_data {
  target = module.pipeline_iam.data.aws_iam_policy_document.redis_access
  values = {
    json = "{\"Sid\": \"RedisAccess\"}"
  }
}

override_data {
  target = module.pipeline_iam.data.aws_iam_policy_document.postgres_access
  values = {
    json = "{\"Sid\": \"PostgresAccess\"}"
  }
}

override_data {
  target = module.pipeline_iam.data.aws_iam_policy_document.s3_access
  values = {
    json = "{\"Sid\": \"S3Access\"}"
  }
}

override_data {
  target = module.pipeline_iam.data.aws_iam_policy_document.opensearch_access
  values = {
    json = "{\"Sid\": \"OpensearchAccess\"}"
  }
}

override_data {
  target = module.pipeline_iam.data.aws_iam_policy_document.iam_access
  values = {
    json = "{\"Sid\": \"IamAccess\"}"
  }
}

override_data {
  target = module.pipeline_iam.data.aws_ssm_parameter.central_log_group_parameter
  values = {
    value = "{\"prod\":\"arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_prod\", \"dev\":\"arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_dev\"}"
  }
}
