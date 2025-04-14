mock_provider "aws" {}

variables {
  aws_account_name = "sandbox-test"
}

run "aws_s3_bucket_unit_test" {
  command = plan

  assert {
    condition     = aws_s3_bucket.terraform-state.bucket == "terraform-platform-state-sandbox-test"
    error_message = "Should be: terraform-platform-state-sandbox-test"
  }

  # Cannot test for the default on a plan
  # aws_s3_bucket.terraform-state.force_destroy == false

  assert {
    condition     = aws_s3_bucket.terraform-state.tags["managed-by"] == "Terraform"
    error_message = "Should be: Terraform statefile storage - DBT Platform"
  }

  assert {
    condition     = aws_s3_bucket.terraform-state.tags["purpose"] == "Terraform statefile storage - DBT Platform"
    error_message = "Should be: Terraform statefile storage - DBT Platform"
  }
}

run "aws_s3_bucket_acl_unit_test" {
  command = plan

  assert {
    condition     = aws_s3_bucket_acl.terraform-state-acl.acl == "private"
    error_message = "Should be: private"
  }
}

run "aws_s3_bucket_versioning_unit_test" {
  command = plan

  assert {
    condition     = aws_s3_bucket_versioning.terraform-state-versioning.versioning_configuration[0].status == "Enabled"
    error_message = "Should be: Enabled"
  }
}

run "aws_s3_bucket_ownership_controls_unit_test" {
  command = plan

  assert {
    condition     = aws_s3_bucket_ownership_controls.terraform-state-ownership.rule[0].object_ownership == "BucketOwnerPreferred"
    error_message = "Should be: 'BucketOwnerPreferred'"
  }
}

run "aws_s3_bucket_public_access_block_unit_test" {
  command = plan

  assert {
    condition     = aws_s3_bucket_public_access_block.block.block_public_acls == true
    error_message = "Should be: true"
  }

  assert {
    condition     = aws_s3_bucket_public_access_block.block.block_public_policy == true
    error_message = "Should be: true"
  }

  assert {
    condition     = aws_s3_bucket_public_access_block.block.ignore_public_acls == true
    error_message = "Should be: true"
  }

  assert {
    condition     = aws_s3_bucket_public_access_block.block.restrict_public_buckets == true
    error_message = "Should be: true"
  }
}

run "aws_s3_bucket_server_side_encryption_configuration_unit_test" {
  command = plan

  assert {
    # This attribute don't have an index to reference, so we have to iterate through it in a couple of for loops.
    # Since this nested for loop returns a tuple ('[]' around the expression), we reference the first entry in each with '[0]'
    condition = [for rule in aws_s3_bucket_server_side_encryption_configuration.terraform-state-sse.rule :
      true if[for sse in rule.apply_server_side_encryption_by_default :
    true if[sse.sse_algorithm == "aws:kms"][0]][0]][0] == true
    error_message = "You must use customer managed KMS keys for server side encryption on this bucket"
  }
}

run "aws_kms_alias_unit_test" {
  command = plan

  # Cannot test for the default on a plan
  # aws_kms_key.terraform-bucket-key.is_enabled == true

  assert {
    condition     = aws_kms_alias.key-alias.name == "alias/terraform-platform-state-s3-key-sandbox-test"
    error_message = "KMS key alias is incorrect"
  }
}


# Cannot test for the default on a plan
# run "aws_kms_key_unit_test" {
#   aws_kms_key.terraform-bucket-key.bypass_policy_lockout_safety_check == false
# }

run "aws_dynamodb_table_unit_test" {
  command = plan

  assert {
    condition     = aws_dynamodb_table.terraform-state.name == "terraform-platform-lockdb-sandbox-test"
    error_message = "Invalid name for dynamoDB table"
  }
  assert {
    condition     = aws_dynamodb_table.terraform-state.read_capacity >= 20
    error_message = "The read_capacity is set too low. Minimum == 20"
  }
  assert {
    condition     = aws_dynamodb_table.terraform-state.write_capacity >= 20
    error_message = "The write_capacity is set too low. Minimum == 20"
  }
  assert {
    condition     = aws_dynamodb_table.terraform-state.hash_key == "LockID"
    error_message = "The DynamoDB table requires the partition (or 'hash') key to be 'LockID'"
  }
  assert {
    condition = [for att in aws_dynamodb_table.terraform-state.attribute :
    true if[att.name == "LockID" && att.type == "S"][0]][0] == true
    error_message = "The 'LockID' key must be of type string ('S')"
  }
}
