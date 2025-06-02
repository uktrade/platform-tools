variables {
  vpc_name         = "s3-test-vpc-name"
  application      = "s3-test-application"
  dns_account_name = "dev"
  environment      = "dev"
  name             = "s3-test-name"
  config = {
    "bucket_name" = "dbt-terraform-test-s3-module",
    "type"        = "string",
    "versioning"  = false,
    "objects"     = [],
  }
}

mock_provider "aws" {}

mock_provider "aws" {
  alias = "domain-cdn"
}

mock_provider "aws" {
  alias = "domain"
}

run "aws_s3_bucket_unit_test" {
  command = plan

  assert {
    condition     = output.bucket_name == "dbt-terraform-test-s3-module"
    error_message = "Should be: dbt-terraform-test-s3-module"
  }

  assert {
    condition     = aws_s3_bucket.this.bucket == "dbt-terraform-test-s3-module"
    error_message = "Invalid name for aws_s3_bucket"
  }

  # Expecting default value for aws_s3_bucket.this.force_destroy == false, which we cannon test on a plan

  assert {
    condition     = aws_s3_bucket.this.tags["environment"] == "dev"
    error_message = "Invalid value for aws_s3_bucket tags parameter."
  }

  assert {
    condition     = aws_s3_bucket.this.tags["application"] == "s3-test-application"
    error_message = "Invalid value for aws_s3_bucket tags parameter."
  }

  assert {
    condition     = aws_s3_bucket.this.tags["copilot-application"] == "s3-test-application"
    error_message = "Invalid value for aws_s3_bucket tags parameter."
  }

  assert {
    condition     = aws_s3_bucket.this.tags["copilot-environment"] == "dev"
    error_message = "Invalid value for aws_s3_bucket tags parameter."
  }

  assert {
    condition     = aws_s3_bucket.this.tags["managed-by"] == "DBT Platform - Terraform"
    error_message = "Invalid value for aws_s3_bucket tags parameter."
  }

  assert {
    condition     = aws_s3_bucket_lifecycle_configuration.lifecycle-configuration == []
    error_message = "Should be: []"
  }

}

run "aws_iam_policy_document_unit_test" {
  command = plan

  assert {
    condition     = [for el in data.aws_iam_policy_document.bucket-policy.statement[0].condition : true if el.variable == "aws:SecureTransport"][0] == true
    error_message = "Should be: aws:SecureTransport"
  }

  assert {
    condition     = data.aws_iam_policy_document.bucket-policy.statement[0].effect == "Deny"
    error_message = "Should be: Deny"
  }

  assert {
    condition     = [for el in data.aws_iam_policy_document.bucket-policy.statement[0].actions : true if el == "s3:*"][0] == true
    error_message = "Should be: s3:*"
  }
}

run "aws_s3_bucket_versioning_unit_test" {
  command = plan

  assert {
    condition     = aws_s3_bucket_versioning.this-versioning.versioning_configuration[0].status == "Disabled"
    error_message = "Should be: Disabled"
  }
}

run "aws_kms_key_unit_test" {
  command = plan

  # Expecting default value for aws_kms_key.kms-key[0].bypass_policy_lockout_safety_check == false, which we cannon test on a plan

  # Expecting default value for aws_kms_key.kms-key[0].customer_master_key_spec == "SYMMETRIC_DEFAULT", which we cannon test on a plan

  # Expecting default value for aws_kms_key.kms-key[0].enable_key_rotation == false, which we cannon test on a plan

  # Expecting default value for aws_kms_key.kms-key[0].is_enabled == true, which we cannon test on a plan

  # Expecting default value for aws_kms_key.kms-key[0].key_usage == "ENCRYPT_DECRYPT", which we cannon test on a plan

  assert {
    condition     = aws_kms_key.kms-key[0].tags["application"] == "s3-test-application"
    error_message = "Invalid value for aws_kms_key tags parameter."
  }

  assert {
    condition     = aws_kms_key.kms-key[0].tags["environment"] == "dev"
    error_message = "Invalid value for aws_kms_key tags parameter."
  }
}

run "aws_kms_alias_unit_test" {
  command = plan

  assert {
    condition     = aws_kms_alias.s3-bucket[0].name == "alias/s3-test-application-dev-dbt-terraform-test-s3-module-key"
    error_message = "Should be: alias/s3-test-application-dev-dbt-terraform-test-s3-module-key"
  }
}

run "aws_s3_bucket_server_side_encryption_configuration_unit_test" {
  command = plan

  assert {
    condition     = [for el in aws_s3_bucket_server_side_encryption_configuration.encryption-config[0].rule : true if[for el2 in el.apply_server_side_encryption_by_default : true if el2.sse_algorithm == "aws:kms"][0] == true][0] == true
    error_message = "Invalid value for aws_s3_bucket_server_side_encryption_configuration tags parameter."
  }
}

run "aws_s3_bucket_versioning_enabled_unit_test" {
  command = plan

  variables {
    config = {
      "bucket_name" = "dbt-terraform-test-s3-module",
      "type"        = "string",
      "versioning"  = true,
      "objects"     = [],
    }
  }

  ### Test aws_s3_bucket_versioning resource ###
  assert {
    condition     = aws_s3_bucket_versioning.this-versioning.versioning_configuration[0].status == "Enabled"
    error_message = "Should be: Enabled"
  }
}

run "aws_s3_bucket_lifecycle_configuration_unit_test" {
  command = plan

  variables {
    config = {
      "bucket_name"     = "dbt-terraform-test-s3-module",
      "type"            = "string",
      "lifecycle_rules" = [{ "filter_prefix" = "/foo", "expiration_days" = 90, "enabled" = true }],
      "objects"         = [],
    }
  }

  ### Test aws_s3_bucket_lifecycle_configuration resource ###
  assert {
    condition     = aws_s3_bucket_lifecycle_configuration.lifecycle-configuration[0].rule[0].filter[0].prefix == "/foo"
    error_message = "Should be: /foo"
  }

  assert {
    condition     = aws_s3_bucket_lifecycle_configuration.lifecycle-configuration[0].rule[0].expiration[0].days == 90
    error_message = "Should be: 90"
  }

  assert {
    condition     = aws_s3_bucket_lifecycle_configuration.lifecycle-configuration[0].rule[0].abort_incomplete_multipart_upload[0].days_after_initiation == 7
    error_message = "Should be: 7"
  }

  assert {
    condition     = aws_s3_bucket_lifecycle_configuration.lifecycle-configuration[0].rule[0].status == "Enabled"
    error_message = "Should be: Enabled"
  }
}

run "aws_s3_bucket_lifecycle_configuration_no_prefix_unit_test" {
  command = plan

  variables {
    config = {
      "bucket_name"     = "dbt-terraform-test-s3-module",
      "type"            = "string",
      "lifecycle_rules" = [{ "expiration_days" = 90, "enabled" = true }],
      "objects"         = [],
    }
  }

  ### Test aws_s3_bucket_lifecycle_configuration resource when no prefix is used ###
  assert {
    condition     = aws_s3_bucket_lifecycle_configuration.lifecycle-configuration[0].rule[0].filter[0] != null
    error_message = "Should be: {}"
  }
}

run "aws_s3_bucket_data_migration_legacy_config_unit_test" {
  command = plan

  variables {
    config = {
      "bucket_name" = "dbt-terraform-test-s3-cross-account",
      "type"        = "s3",
      "data_migration" = {
        "import" = {
          "worker_role_arn"    = "arn:aws:iam::1234:role/service-role/my-privileged-arn",
          "source_kms_key_arn" = "arn:aws:iam::1234:my-external-kms-key-arn",
          "source_bucket_arn"  = "arn:aws:s3::1234:my-source-bucket"
        }
      }
    }
  }

  assert {
    condition     = module.data_migration[0].module_exists
    error_message = "data migration module should be created"
  }

  assert {
    condition     = module.data_migration[0].sources[0].worker_role_arn == "arn:aws:iam::1234:role/service-role/my-privileged-arn"
    error_message = "data migration worker_role_arn should be present"
  }

  assert {
    condition     = module.data_migration[0].sources[0].source_kms_key_arn == "arn:aws:iam::1234:my-external-kms-key-arn"
    error_message = "data migration worker_role_arn should be present"
  }

  assert {
    condition     = module.data_migration[0].sources[0].source_bucket_arn == "arn:aws:s3::1234:my-source-bucket"
    error_message = "data migration worker_role_arn should be present"
  }
}

run "aws_s3_bucket_data_migration_unit_test" {
  command = plan

  variables {
    config = {
      "bucket_name" = "dbt-terraform-test-s3-cross-account",
      "type"        = "s3",
      "data_migration" = {
        "import_sources" = [
          {
            "worker_role_arn"    = "arn:aws:iam::1234:role/service-role/my-privileged-arn",
            "source_kms_key_arn" = "arn:aws:iam::1234:my-external-kms-key-arn",
            "source_bucket_arn"  = "arn:aws:s3::1234:my-source-bucket"
          },
          {
            "worker_role_arn"    = "arn:aws:iam::1234:role/service-role/my-privileged-arn-2",
            "source_kms_key_arn" = "arn:aws:iam::1234:my-external-kms-key-arn-2",
            "source_bucket_arn"  = "arn:aws:s3::1234:my-source-bucket-2"
          },
        ]
      }
    }
  }

  assert {
    condition     = module.data_migration[0].module_exists
    error_message = "data migration module should be created"
  }

  assert {
    condition     = module.data_migration[0].sources[0].worker_role_arn == "arn:aws:iam::1234:role/service-role/my-privileged-arn"
    error_message = "data migration worker_role_arn should be present"
  }

  assert {
    condition     = module.data_migration[0].sources[0].source_kms_key_arn == "arn:aws:iam::1234:my-external-kms-key-arn"
    error_message = "data migration worker_role_arn should be present"
  }

  assert {
    condition     = module.data_migration[0].sources[0].source_bucket_arn == "arn:aws:s3::1234:my-source-bucket"
    error_message = "data migration worker_role_arn should be present"
  }

  assert {
    condition     = module.data_migration[0].sources[1].worker_role_arn == "arn:aws:iam::1234:role/service-role/my-privileged-arn-2"
    error_message = "data migration worker_role_arn should be present"
  }

  assert {
    condition     = module.data_migration[0].sources[1].source_kms_key_arn == "arn:aws:iam::1234:my-external-kms-key-arn-2"
    error_message = "data migration source_kms_key_arn should be present"
  }

  assert {
    condition     = module.data_migration[0].sources[1].source_bucket_arn == "arn:aws:s3::1234:my-source-bucket-2"
    error_message = "data migration source_bucket_arn should be present"
  }
}

run "aws_s3_bucket_not_data_migration_unit_test" {
  command = plan

  variables {
    config = {
      "bucket_name" = "dbt-terraform-test-s3-not-x-account",
      "type"        = "s3",
    }
  }

  assert {
    condition     = length(module.data_migration) == 0
    error_message = "data migration module should not be created"
  }
}

run "aws_s3_bucket_external_role_access_read_write_unit_test" {
  command = plan

  variables {
    config = {
      "bucket_name" = "dbt-terraform-test-s3-external-role-access",
      "type"        = "s3",
      "external_role_access" = {
        "test-access" = {
          "role_arn"          = "arn:aws:iam::123456789012:role/service-role/my-privileged-arn",
          "read"              = true,
          "write"             = true,
          "cyber_sign_off_by" = "test@businessandtrade.gov.uk"
        }
      }
    }
  }

  assert {
    condition     = length(aws_s3_bucket_policy.bucket-policy) == 1
    error_message = "Should be a bucket policy"
  }

  assert {
    condition     = data.aws_iam_policy_document.bucket-policy.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }

  assert {
    condition = alltrue([
      contains(data.aws_iam_policy_document.bucket-policy.statement[1].actions, "s3:Get*"),
      contains(data.aws_iam_policy_document.bucket-policy.statement[1].actions, "s3:Put*"),
      contains(data.aws_iam_policy_document.bucket-policy.statement[1].actions, "s3:ListBucket"),
    ])
    error_message = "Should be: s3:Get*, s3:Put*, s3:ListBucket"
  }

  assert {
    condition     = length(aws_kms_key_policy.key-policy) == 1
    error_message = "Should be a single kms key policy"
  }

  assert {
    condition     = data.aws_iam_policy_document.key-policy[0].statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }

  assert {
    condition = alltrue([
      contains(data.aws_iam_policy_document.key-policy[0].statement[1].actions, "kms:Decrypt"),
      contains(data.aws_iam_policy_document.key-policy[0].statement[1].actions, "kms:GenerateDataKey"),
    ])
    error_message = "Should be: kms:Decrypt, kms:GenerateDataKey"
  }
}

run "aws_s3_bucket_external_role_access_read_only_unit_test" {
  command = plan

  variables {
    config = {
      "bucket_name" = "dbt-terraform-test-s3-external-role-access",
      "type"        = "s3",
      "external_role_access" = {
        "test-access" = {
          "role_arn"          = "arn:aws:iam::123456789012:role/service-role/my-privileged-arn",
          "read"              = true,
          "write"             = false,
          "cyber_sign_off_by" = "test@businessandtrade.gov.uk"
        }
      }
    }
  }

  assert {
    condition     = length(aws_s3_bucket_policy.bucket-policy) == 1
    error_message = "Should be a bucket policy"
  }

  assert {
    condition     = data.aws_iam_policy_document.bucket-policy.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }

  assert {
    condition = alltrue([
      contains(data.aws_iam_policy_document.bucket-policy.statement[1].actions, "s3:Get*"),
      contains(data.aws_iam_policy_document.bucket-policy.statement[1].actions, "s3:ListBucket"),
      !contains(data.aws_iam_policy_document.bucket-policy.statement[1].actions, "s3:Put*"),
    ])
    error_message = "Should be: s3:Get*, s3:ListBucket"
  }

  assert {
    condition     = length(aws_kms_key_policy.key-policy) == 1
    error_message = "Should be a kms key policy"
  }

  assert {
    condition     = data.aws_iam_policy_document.key-policy[0].statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }

  assert {
    condition = alltrue([
      contains(data.aws_iam_policy_document.key-policy[0].statement[1].actions, "kms:Decrypt"),
      !contains(data.aws_iam_policy_document.key-policy[0].statement[1].actions, "kms:GenerateDataKey"),
    ])
    error_message = "Should be: kms:Decrypt"
  }
}

run "aws_s3_bucket_external_role_access_write_only_unit_test" {
  command = plan

  variables {
    config = {
      "bucket_name" = "dbt-terraform-test-s3-external-role-access",
      "type"        = "s3",
      "external_role_access" = {
        "test-access" = {
          "role_arn"          = "arn:aws:iam::123456789012:role/service-role/my-privileged-arn",
          "read"              = false,
          "write"             = true,
          "cyber_sign_off_by" = "test@businessandtrade.gov.uk"
        }
      }
    }
  }

  assert {
    condition     = length(aws_s3_bucket_policy.bucket-policy) == 1
    error_message = "Should be a bucket policy"
  }

  assert {
    condition     = data.aws_iam_policy_document.bucket-policy.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }

  assert {
    condition = alltrue([
      !contains(data.aws_iam_policy_document.bucket-policy.statement[1].actions, "s3:Get*"),
      !contains(data.aws_iam_policy_document.bucket-policy.statement[1].actions, "s3:ListBucket"),
      contains(data.aws_iam_policy_document.bucket-policy.statement[1].actions, "s3:Put*"),
    ])
    error_message = "Should be: s3:Put*"
  }

  assert {
    condition     = length(aws_kms_key_policy.key-policy) == 1
    error_message = "Should be a kms key policy"
  }

  assert {
    condition     = data.aws_iam_policy_document.key-policy[0].statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }

  assert {
    condition = alltrue([
      !contains(data.aws_iam_policy_document.key-policy[0].statement[1].actions, "kms:Decrypt"),
      contains(data.aws_iam_policy_document.key-policy[0].statement[1].actions, "kms:GenerateDataKey"),
    ])
    error_message = "Should be: kms:GenerateDataKey"
  }
}

run "aws_s3_bucket_external_role_access_invalid_cyber_sign_off" {
  command = plan

  variables {
    config = {
      "bucket_name" = "dbt-terraform-test-s3-external-role-access",
      "type"        = "s3",
      "external_role_access" = {
        "test-access" = {
          "role_arn"          = "arn:aws:iam::123456789012:role/service-role/my-privileged-arn",
          "read"              = true,
          "write"             = true,
          "cyber_sign_off_by" = ""
        }
      }
    }
  }
  expect_failures = [var.config.external_role_access.cyber_sign_off_by]
}

run "aws_s3_bucket_cross_environment_service_access_read_write_unit_test" {
  command = plan

  variables {
    config = {
      "bucket_name" = "dbt-terraform-test-s3-cross-env-service-access",
      "type"        = "s3",
      "cross_environment_service_access" = {
        "test-access" = {
          "environment"       = "test",
          "account"           = "123456789012",
          "service"           = "service",
          "read"              = true,
          "write"             = true,
          "cyber_sign_off_by" = "test@businessandtrade.gov.uk"
        }
      }
    }
  }

  assert {
    condition     = data.aws_iam_policy_document.bucket-policy.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }

  assert {
    condition     = length([for item in data.aws_iam_policy_document.bucket-policy.statement[1].condition : item if item.test == "StringLike"]) == 1
    error_message = "condition should have a test: StringLike attribute"
  }

  assert {
    condition     = length([for item in data.aws_iam_policy_document.bucket-policy.statement[1].condition : item if item.variable == "aws:PrincipalArn"]) == 1
    error_message = "condition should have a variable: aws:PrincipalArn attribute"
  }

  assert {
    condition = length([for item in data.aws_iam_policy_document.bucket-policy.statement[1].condition :
    item if item.values == tolist(["arn:aws:iam::123456789012:role/s3-test-application-test-service-TaskRole-*"])]) == 1
    error_message = "condition should have a values: [bucket arn] attribute"
  }

  assert {
    condition = alltrue([
      contains(data.aws_iam_policy_document.bucket-policy.statement[1].actions, "s3:Get*"),
      contains(data.aws_iam_policy_document.bucket-policy.statement[1].actions, "s3:Put*"),
      contains(data.aws_iam_policy_document.bucket-policy.statement[1].actions, "s3:ListBucket"),
    ])
    error_message = "Should be: s3:Get*, s3:Put*, s3:ListBucket"
  }
}

run "aws_s3_bucket_cross_environment_service_access_read_only_unit_test" {
  command = plan

  variables {
    config = {
      "bucket_name" = "dbt-terraform-test-s3-cross-env-service-access",
      "type"        = "s3",
      "cross_environment_service_access" = {
        "test-access" = {
          "environment"       = "test",
          "account"           = "123456789012",
          "service"           = "service",
          "read"              = true,
          "write"             = false,
          "cyber_sign_off_by" = "test@businessandtrade.gov.uk"
        }
      }
    }
  }

  assert {
    condition     = data.aws_iam_policy_document.bucket-policy.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }

  assert {
    condition = alltrue([
      contains(data.aws_iam_policy_document.bucket-policy.statement[1].actions, "s3:Get*"),
      contains(data.aws_iam_policy_document.bucket-policy.statement[1].actions, "s3:ListBucket"),
      !contains(data.aws_iam_policy_document.bucket-policy.statement[1].actions, "s3:Put*"),
    ])
    error_message = "Should be: s3:Get*, s3:ListBucket"
  }
}

run "aws_s3_bucket_cross_environment_service_access_write_only_unit_test" {
  command = plan

  variables {
    config = {
      "bucket_name" = "dbt-terraform-test-s3-cross-env-service-access",
      "type"        = "s3",
      "cross_environment_service_access" = {
        "test-access" = {
          "environment"       = "test",
          "account"           = "123456789012",
          "service"           = "service",
          "read"              = false,
          "write"             = true,
          "cyber_sign_off_by" = "test@businessandtrade.gov.uk"
        }
      }
    }
  }

  assert {
    condition     = data.aws_iam_policy_document.bucket-policy.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }

  assert {
    condition = alltrue([
      !contains(data.aws_iam_policy_document.bucket-policy.statement[1].actions, "s3:Get*"),
      !contains(data.aws_iam_policy_document.bucket-policy.statement[1].actions, "s3:ListBucket"),
      contains(data.aws_iam_policy_document.bucket-policy.statement[1].actions, "s3:Put*"),
    ])
    error_message = "Should be: s3:Put*"
  }
}

run "aws_s3_bucket_cross_environment_service_access_invalid_cyber_sign_off" {
  command = plan

  variables {
    config = {
      "bucket_name" = "dbt-terraform-test-s3-cross-env-service-access",
      "type"        = "s3",
      "cross_environment_service_access" = {
        "test-access" = {
          "environment"       = "test",
          "account"           = "123456789012",
          "service"           = "service",
          "read"              = true,
          "write"             = true,
          "cyber_sign_off_by" = "no-one"
        }
      }
    }
  }
  expect_failures = [var.config.cross_environment_service_access.cyber_sign_off_by]
}

run "aws_s3_bucket_object_lock_configuration_governance_unit_test" {
  command = plan

  variables {
    config = {
      "bucket_name"      = "dbt-terraform-test-s3-module",
      "type"             = "string",
      "versioning"       = true,
      "retention_policy" = { "mode" = "GOVERNANCE", "days" = 1 },
      "objects"          = [],
    }
  }

  assert {
    condition     = [for el in aws_s3_bucket_object_lock_configuration.object-lock-config[0].rule : true if el.default_retention[0].mode == "GOVERNANCE"][0] == true
    error_message = "Should be: GOVERNANCE"
  }

  assert {
    condition     = [for el in aws_s3_bucket_object_lock_configuration.object-lock-config[0].rule : true if el.default_retention[0].days == 1][0] == true
    error_message = "Should be: 1"
  }
}

run "aws_s3_bucket_object_lock_configuration_compliance_unit_test" {
  command = plan

  variables {
    config = {
      "bucket_name"      = "dbt-terraform-test-s3-module",
      "type"             = "string",
      "versioning"       = true,
      "retention_policy" = { "mode" = "COMPLIANCE", "years" = 1 },
      "objects"          = [],
    }
  }

  assert {
    condition     = [for el in aws_s3_bucket_object_lock_configuration.object-lock-config[0].rule : true if el.default_retention[0].mode == "COMPLIANCE"][0] == true
    error_message = "Invalid s3 bucket object lock configuration"
  }

  assert {
    condition     = [for el in aws_s3_bucket_object_lock_configuration.object-lock-config[0].rule : true if el.default_retention[0].years == 1][0] == true
    error_message = "Invalid s3 bucket object lock configuration"
  }
}

run "aws_s3_bucket_object_lock_configuration_nopolicy_unit_test" {
  command = plan

  variables {
    config = {
      "bucket_name" = "dbt-terraform-test-s3-module",
      "type"        = "string",
      "versioning"  = true,
      "objects"     = [],
    }
  }

  ### Test aws_s3_bucket_object_lock_configuration resource ###
  assert {
    condition     = aws_s3_bucket_object_lock_configuration.object-lock-config == []
    error_message = "Invalid s3 bucket object lock configuration"
  }
}

run "aws_cloudfront_origin_access_control_unit_test" {
  command = plan

  variables {
    config = {
      "bucket_name"          = "test",
      "type"                 = "string",
      "serve_static_content" = true,
      "objects"              = [],
    }
  }

  assert {
    condition     = aws_cloudfront_origin_access_control.oac[0].name == "test.dev.s3-test-application-oac"
    error_message = "Invalid value for aws_cloudfront_origin_access_control name."
  }

  assert {
    condition     = aws_cloudfront_origin_access_control.oac[0].description == "Origin access control for Cloudfront distribution and test.dev.s3-test-application.uktrade.digital static s3 bucket."
    error_message = "Invalid value for aws_cloudfront_origin_access_control name."
  }

  assert {
    condition     = aws_cloudfront_origin_access_control.oac[0].origin_access_control_origin_type == "s3"
    error_message = "Invalid value for aws_cloudfront_origin_access_control origin type."
  }

  assert {
    condition     = aws_cloudfront_origin_access_control.oac[0].signing_behavior == "always"
    error_message = "Invalid value for aws_cloudfront_origin_access_control signing_behavior."
  }

  assert {
    condition     = aws_cloudfront_origin_access_control.oac[0].signing_protocol == "sigv4"
    error_message = "Invalid value for aws_cloudfront_origin_access_control signing protocol."
  }
}

run "aws_acm_certificate_unit_test" {
  command = plan

  variables {
    config = {
      "bucket_name"          = "test",
      "serve_static_content" = true,
      "type"                 = "string",
      "objects"              = [],
    }
  }

  assert {
    condition     = aws_acm_certificate.certificate[0].domain_name == "test.dev.s3-test-application.uktrade.digital"
    error_message = "Invalid value for aws_acm_certificate domain name."
  }

  assert {
    condition     = aws_acm_certificate.certificate[0].validation_method == "DNS"
    error_message = "Invalid value for aws_acm_certificate validation method."
  }

  assert {
    condition     = aws_acm_certificate.certificate[0].tags["application"] == "s3-test-application"
    error_message = "Invalid value for aws_acm_certificate tags parameter."
  }

  assert {
    condition     = aws_acm_certificate.certificate[0].tags["environment"] == "dev"
    error_message = "Invalid value for aws_acm_certificate tags parameter."
  }

  assert {
    condition     = aws_acm_certificate.certificate[0].tags["application"] == "s3-test-application"
    error_message = "Invalid value for aws_acm_certificate tags parameter."
  }

  assert {
    condition     = aws_acm_certificate.certificate[0].tags["copilot-application"] == "s3-test-application"
    error_message = "Invalid value for aws_acm_certificate tags parameter."
  }

  assert {
    condition     = aws_acm_certificate.certificate[0].tags["copilot-environment"] == "dev"
    error_message = "Invalid value for aws_acm_certificate tags parameter."
  }

  assert {
    condition     = aws_acm_certificate.certificate[0].tags["managed-by"] == "DBT Platform - Terraform"
    error_message = "Invalid value for aws_acm_certificate tags parameter."
  }
}

run "aws_route53_record_cert_validation_unit_test" {
  command = plan

  variables {
    config = {
      "bucket_name"          = "test",
      "serve_static_content" = true,
      "type"                 = "string",
      "objects"              = [],
    }
  }

  # assert {
  #   condition     = aws_route53_record.cert_validation[0].type == "CNAME"
  #   error_message = "Invalid value for aws_route53_record cert validation type."
  # }

  assert {
    condition     = aws_route53_record.cert_validation[0].ttl == 60
    error_message = "Invalid TTL value for aws_route53_record cert validation."
  }
}

# ADD E2E for aws_acm_certificate_validation

run "aws_route53_record_cloudfront_domain_unit_test" {
  command = plan

  variables {
    config = {
      "bucket_name"          = "test",
      "serve_static_content" = true,
      "type"                 = "string",
      "objects"              = [],
    }
  }

  # assert {
  #   condition     = aws_route53_record.cloudfront_domain[0].name == aws_s3_bucket.this.bucket
  #   error_message = "Route 53 record name should match the S3 bucket name."
  # } MOVE TO E2E

  assert {
    condition     = aws_route53_record.cloudfront_domain[0].type == "A"
    error_message = "Route 53 record type should be 'A'."
  }

  # assert {
  #   condition     = aws_route53_record.cloudfront_domain[0].zone_id == data.aws_route53_zone.selected[0].id
  #   error_message = "Route 53 record zone ID should match the selected Route 53 zone ID."
  # } MOVE TO E2E

  # assert {
  #   condition     = aws_route53_record.cloudfront_domain[0].alias[0].name == aws_cloudfront_distribution.s3_distribution[0].domain_name
  #   error_message = "Route 53 alias name should match the CloudFront distribution domain name."
  # } MOVE TO E2E

  # assert {
  #   condition     = aws_route53_record.cloudfront_domain[0].alias[0].zone_id == aws_cloudfront_distribution.s3_distribution[0].hosted_zone_id
  #   error_message = "Route 53 alias zone ID should match the CloudFront distribution hosted zone ID."
  # } MOVE TO E2E

  assert {
    condition     = aws_route53_record.cloudfront_domain[0].alias[0].evaluate_target_health == false
    error_message = "Route 53 alias should not evaluate target health."
  }

}


run "aws_cloudfront_distribution_unit_test" {
  command = plan

  variables {
    config = {
      "bucket_name"          = "test",
      "serve_static_content" = true,
      "type"                 = "string",
      "objects"              = [],
    }
  }

  assert {
    condition     = aws_cloudfront_distribution.s3_distribution[0].enabled == true
    error_message = "CloudFront distribution should be enabled."
  }

  assert {
    condition     = contains(aws_cloudfront_distribution.s3_distribution[0].aliases, "test.dev.s3-test-application.uktrade.digital")
    error_message = "CloudFront distribution should include the correct alias."
  }

  assert {
    condition     = length(aws_cloudfront_distribution.s3_distribution[0].default_cache_behavior[0].allowed_methods) == 2 && contains(aws_cloudfront_distribution.s3_distribution[0].default_cache_behavior[0].allowed_methods, "GET") && contains(aws_cloudfront_distribution.s3_distribution[0].default_cache_behavior[0].allowed_methods, "HEAD")
    error_message = "Cloudfront distribution default_cache_behavior allowed methods should contain GET and HEAD."
  }

  assert {
    condition     = length(aws_cloudfront_distribution.s3_distribution[0].default_cache_behavior[0].cached_methods) == 2 && contains(aws_cloudfront_distribution.s3_distribution[0].default_cache_behavior[0].cached_methods, "GET") && contains(aws_cloudfront_distribution.s3_distribution[0].default_cache_behavior[0].cached_methods, "HEAD")
    error_message = "Cloudfront distribution default_cache_behavior cached methods should contain GET and HEAD."
  }

  assert {
    condition     = aws_cloudfront_distribution.s3_distribution[0].default_cache_behavior[0].viewer_protocol_policy == "redirect-to-https"
    error_message = "CloudFront should enforce HTTPS."
  }

  assert {
    condition     = aws_cloudfront_distribution.s3_distribution[0].viewer_certificate[0].ssl_support_method == "sni-only"
    error_message = "Cloudfront viewer certificate ssl support method should be sni-only."
  }

  assert {
    condition     = aws_cloudfront_distribution.s3_distribution[0].viewer_certificate[0].minimum_protocol_version == "TLSv1.2_2021"
    error_message = "Cloudfront viewer certificate minimum_protocol_version should be TLSv1.2_2021."
  }

  assert {
    condition     = aws_cloudfront_distribution.s3_distribution[0].restrictions[0].geo_restriction[0].restriction_type == "none"
    error_message = "Cloudfront geo restrictions should be none."
  }

  assert {
    condition     = aws_ssm_parameter.cloudfront_alias[0].tags["environment"] == "dev"
    error_message = "Invalid value for aws_s3_bucket tags parameter."
  }

  assert {
    condition     = aws_ssm_parameter.cloudfront_alias[0].tags["application"] == "s3-test-application"
    error_message = "Invalid value for aws_s3_bucket tags parameter."
  }

  assert {
    condition     = aws_ssm_parameter.cloudfront_alias[0].tags["copilot-application"] == "s3-test-application"
    error_message = "Invalid value for aws_s3_bucket tags parameter."
  }

  assert {
    condition     = aws_ssm_parameter.cloudfront_alias[0].tags["copilot-environment"] == "dev"
    error_message = "Invalid value for aws_s3_bucket tags parameter."
  }

  assert {
    condition     = aws_ssm_parameter.cloudfront_alias[0].tags["managed-by"] == "DBT Platform - Terraform"
    error_message = "Invalid value for aws_s3_bucket tags parameter."
  }
}

# run "aws_s3_bucket_policy_cloudfront_unit_test" {    TEST IN E2E instead
#   command = plan

#   variables {
#     config = {
#       "bucket_name" = "test",
#       "serve_static_content" = true,
#       "type"        = "string",
#       "objects"     = [],
#     }
#   }

#   assert {
#     condition     = contains(tolist([aws_s3_bucket_policy.cloudfront_bucket_policy[0].policy]), "cloudfront.amazonaws.com")
#     error_message = "S3 bucket policy should allow CloudFront access."
#   }
# }


# run "aws_kms_key_policy_s3_ssm_kms_key_policy_test" {   TEST IN E2E
#   command = plan

#   variables {
#     config = {
#       "bucket_name" = "test",
#       "serve_static_content" = true,
#       "type"        = "string",
#       "objects"     = [],
#     }
#   }

#   assert {
#     condition     = aws_kms_key_policy.s3-ssm-kms-key-policy[0].policy != null
#     error_message = "KMS key policy should contain a valid policy document."
#   }

#   assert {
#     condition     = contains(aws_kms_key_policy.s3-ssm-kms-key-policy[0].policy, "ssm.amazonaws.com")
#     error_message = "KMS key policy should allow access to ssm.amazonaws.com."
#   }

#   assert {
#     condition     = contains(aws_kms_key_policy.s3-ssm-kms-key-policy[0].policy, "kms:Decrypt")
#     error_message = "KMS key policy should allow kms:Decrypt action."
#   }

#   assert {
#     condition     = contains(aws_kms_key_policy.s3-ssm-kms-key-policy[0].policy, "kms:GenerateDataKey*")
#     error_message = "KMS key policy should allow kms:GenerateDataKey* action."
#   }

#   assert {
#     condition     = contains(aws_kms_key_policy.s3-ssm-kms-key-policy[0].policy, "/copilot/s3-test-application/dev/secrets/STATIC_S3_ENDPOINT")
#     error_message = "KMS key policy should include the correct SSM parameter name for encryption context."
#   }

#   assert {
#     condition     = contains(aws_kms_key_policy.s3-ssm-kms-key-policy[0].policy, "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root")
#     error_message = "KMS key policy should allow root account full access."
#   }
# }


run "aws_ssm_parameter_cloudfront_alias_unit_test" {
  command = plan

  variables {
    config = {
      "bucket_name"          = "test",
      "serve_static_content" = true,
      "type"                 = "string",
      "objects"              = [],
    }
  }

  assert {
    condition     = aws_ssm_parameter.cloudfront_alias[0].name == "/copilot/s3-test-application/dev/secrets/STATIC_S3_ENDPOINT"
    error_message = "Invalid name for aws_ssm_parameter cloudfront alias."
  }

  assert {
    condition     = aws_ssm_parameter.cloudfront_alias[0].type == "SecureString"
    error_message = "Invalid type for aws_ssm_parameter cloudfront alias."
  }

  assert {
    condition     = aws_ssm_parameter.cloudfront_alias[0].value == "test.dev.s3-test-application.uktrade.digital"
    error_message = "Invalid value for aws_ssm_parameter cloudfront alias."
  }

  assert {
    condition     = aws_ssm_parameter.cloudfront_alias[0].tags["environment"] == "dev"
    error_message = "Invalid value for aws_s3_bucket tags parameter."
  }

  assert {
    condition     = aws_ssm_parameter.cloudfront_alias[0].tags["application"] == "s3-test-application"
    error_message = "Invalid value for aws_s3_bucket tags parameter."
  }

  assert {
    condition     = aws_ssm_parameter.cloudfront_alias[0].tags["copilot-application"] == "s3-test-application"
    error_message = "Invalid value for aws_s3_bucket tags parameter."
  }

  assert {
    condition     = aws_ssm_parameter.cloudfront_alias[0].tags["copilot-environment"] == "dev"
    error_message = "Invalid value for aws_s3_bucket tags parameter."
  }

  assert {
    condition     = aws_ssm_parameter.cloudfront_alias[0].tags["managed-by"] == "DBT Platform - Terraform"
    error_message = "Invalid value for aws_s3_bucket tags parameter."
  }
}

run "aws_serve_static_param_name_override_unit_test" {
  command = plan

  variables {
    config = {
      "bucket_name"             = "test",
      "serve_static_content"    = true,
      "type"                    = "string",
      "objects"                 = [],
      "serve_static_param_name" = "ALTERNATIVE_STATIC_S3_ENDPOINT"
    }
  }

  assert {
    condition     = aws_ssm_parameter.cloudfront_alias[0].name == "/copilot/s3-test-application/dev/secrets/ALTERNATIVE_STATIC_S3_ENDPOINT"
    error_message = "Invalid name for aws_ssm_parameter cloudfront alias."
  }
}

run "aws_ssm_parameter_cloudfront_alias_prod_domain_name_unit_test" {
  command = plan

  variables {
    config = {
      "bucket_name"          = "test",
      "serve_static_content" = true,
      "type"                 = "string",
      "objects"              = [],
    }
    environment = "prod"
  }

  assert {
    condition     = aws_ssm_parameter.cloudfront_alias[0].value == "test.s3-test-application.prod.uktrade.digital"
    error_message = "Invalid value for aws_ssm_parameter cloudfront alias."
  }

  assert {
    condition     = aws_cloudfront_origin_access_control.oac[0].description == "Origin access control for Cloudfront distribution and test.s3-test-application.prod.uktrade.digital static s3 bucket."
    error_message = "Invalid value for aws_cloudfront_origin_access_control name."
  }

  assert {
    condition     = aws_acm_certificate.certificate[0].domain_name == "test.s3-test-application.prod.uktrade.digital"
    error_message = "Invalid value for aws_acm_certificate domain name."
  }

  assert {
    condition     = contains(aws_cloudfront_distribution.s3_distribution[0].aliases, "test.s3-test-application.prod.uktrade.digital")
    error_message = "CloudFront distribution should include the correct alias."
  }

  assert {
    condition     = aws_ssm_parameter.cloudfront_alias[0].value == "test.s3-test-application.prod.uktrade.digital"
    error_message = "Invalid value for aws_ssm_parameter cloudfront alias."
  }

  assert {
    condition     = aws_ssm_parameter.cloudfront_alias[0].value == "test.s3-test-application.prod.uktrade.digital"
    error_message = "Invalid value for aws_ssm_parameter cloudfront alias."
  }
}
