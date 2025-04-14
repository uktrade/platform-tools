mock_provider "aws" {}

variables {
  sources = [
    {
      "source_bucket_arn"  = "test-source-bucket-arn"
      "source_kms_key_arn" = "test-source-kms-key-arn"
      "worker_role_arn"    = "test-role-arn"
    },
    {
      "source_bucket_arn" = "test-source-bucket-arn-2"
      "worker_role_arn"   = "test-role-arn-2"
    }
  ]
  destination_bucket_arn        = "test-destination-bucket-arn"
  destination_bucket_identifier = "test-destination-bucket-name"
}

override_data {
  target = data.aws_iam_policy_document.allow_assume_role
  values = {
    json = "{\"Sid\": \"AllowAssumeWorkerRole\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.s3_migration_policy_document
  values = {
    json = "{\"Sid\": \"AllowReadOnSourceBucket\"}"
  }
}

run "data_migration_unit_test" {
  command = plan

  assert {
    condition     = aws_iam_role.s3_migration_role.name == "test-destination-bucket-name-S3MigrationRole"
    error_message = "Should be: test-destination-bucket-name-S3MigrationRole"
  }

  # Check that the correct aws_iam_policy_document is used from the mocked data json
  assert {
    condition     = aws_iam_role.s3_migration_role.assume_role_policy == "{\"Sid\": \"AllowAssumeWorkerRole\"}"
    error_message = "Should be: {\"Sid\": \"AllowAssumeWorkerRole\"}"
  }

  assert {
    condition     = aws_iam_role_policy.s3_migration_policy.name == "test-destination-bucket-name-S3MigrationPolicy"
    error_message = "Should be: test-destination-bucket-name-S3MigrationPolicy"
  }

  assert {
    condition     = aws_iam_role_policy.s3_migration_policy.role == "test-destination-bucket-name-S3MigrationRole"
    error_message = "Should be: test-destination-bucket-name-S3MigrationRole"
  }

  # Check that the correct aws_iam_policy_document is used from the mocked data json
  assert {
    condition     = aws_iam_role_policy.s3_migration_policy.policy == "{\"Sid\": \"AllowReadOnSourceBucket\"}"
    error_message = "Should be: {\"Sid\": \"AllowReadOnSourceBucket\"}"
  }

  # Check the contents of the policy document
  assert {
    condition     = contains(data.aws_iam_policy_document.s3_migration_policy_document.statement[1].resources, "test-destination-bucket-arn")
    error_message = "Should contain: test-destination-bucket-arn"
  }
  assert {
    condition     = contains(data.aws_iam_policy_document.s3_migration_policy_document.statement[3].actions, "kms:Decrypt")
    error_message = "Statement should contain kms:Decrypt"
  }
  # source buckets
  assert {
    condition     = length(data.aws_iam_policy_document.s3_migration_policy_document.statement[0].resources) == 4
    error_message = "Should have 4 elements"
  }
  assert {
    condition     = contains(data.aws_iam_policy_document.s3_migration_policy_document.statement[0].resources, "test-source-bucket-arn")
    error_message = "Should contain: test-source-bucket-arn"
  }
  assert {
    condition     = contains(data.aws_iam_policy_document.s3_migration_policy_document.statement[0].resources, "test-source-bucket-arn/*")
    error_message = "Should contain: test-source-bucket-arn/*"
  }
  assert {
    condition     = contains(data.aws_iam_policy_document.s3_migration_policy_document.statement[0].resources, "test-source-bucket-arn-2")
    error_message = "Should contain: test-source-bucket-arn-2"
  }
  assert {
    condition     = contains(data.aws_iam_policy_document.s3_migration_policy_document.statement[0].resources, "test-source-bucket-arn-2/*")
    error_message = "Should contain: test-source-bucket-arn-2/*"
  }
  # worker arns
  assert {
    condition     = length(tolist(data.aws_iam_policy_document.allow_assume_role.statement[0].principals)[0].identifiers) == 2
    error_message = "Should have 2 elements"
  }
  assert {
    condition     = contains(tolist(data.aws_iam_policy_document.allow_assume_role.statement[0].principals)[0].identifiers, "test-role-arn")
    error_message = "Should contain: test-role-arn"
  }
  assert {
    condition     = contains(tolist(data.aws_iam_policy_document.allow_assume_role.statement[0].principals)[0].identifiers, "test-role-arn-2")
    error_message = "Should contain: test-role-arn-2"
  }
  # kms keys
  assert {
    condition     = length(data.aws_iam_policy_document.s3_migration_policy_document.statement[3].resources) == 1
    error_message = "Should have 1 elements"
  }
  assert {
    condition     = contains(data.aws_iam_policy_document.s3_migration_policy_document.statement[3].resources, "test-source-kms-key-arn")
    error_message = "Should contain: test-source-kms-key-arn"
  }
}

run "data_migration_without_source_kms_key" {
  command = plan

  variables {
    sources = [
      {
        "source_bucket_arn" = "test-source-bucket-arn"
        "worker_role_arn"   = "test-role-arn"
      }
    ]
    destination_bucket_arn        = "test-destination-bucket-arn"
    destination_bucket_identifier = "test-destination-bucket-name"
  }

  assert {
    # Cannot check the specific statement, because it does not exist
    condition     = strcontains(jsonencode(data.aws_iam_policy_document.s3_migration_policy_document), "kms:Decrypt") == false
    error_message = "Statement should not contain kms:Decrypt"
  }
}
