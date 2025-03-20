variables {
  aws_account_name = "sandbox-test"
}

run "aws_s3_bucket_e2e_test" {
  command = apply

  # Terraform state
  assert {
    condition     = aws_s3_bucket.terraform-state.id == "terraform-platform-state-sandbox-test"
    error_message = "Should be: terraform-platform-state-sandbox-test"
  }

  assert {
    condition     = aws_s3_bucket.terraform-state.request_payer == "BucketOwner"
    error_message = "Should be: BucketOwner"
  }

  assert {
    condition     = aws_s3_bucket.terraform-state.object_lock_enabled == false
    error_message = "Should be: false"
  }

  assert {
    condition     = [for el in aws_s3_bucket.terraform-state.grant : true if[for el2 in el.permissions : true if el2 == "FULL_CONTROL"][0]][0] == true
    error_message = "Should be: FULL_CONTROL"
  }

  assert {
    condition     = [for el in aws_s3_bucket.terraform-state.versioning : true if el.enabled == false][0] == true
    error_message = "Should be: true"
  }

  assert {
    condition     = [for el in aws_s3_bucket.terraform-state.versioning : true if el.mfa_delete == false][0] == true
    error_message = "Should be: true"
  }

  # ACL
  assert {
    condition     = aws_s3_bucket_acl.terraform-state-acl.bucket == aws_s3_bucket.terraform-state.id
    error_message = "The bucket ACL resource is not attached to the correct S3 bucket"
  }

  assert {
    condition     = aws_s3_bucket_acl.terraform-state-acl.id == "terraform-platform-state-sandbox-test,private"
    error_message = "Should be:terraform-platform-state-sandbox-test,private"
  }

  # Versioning
  assert {
    condition     = aws_s3_bucket_versioning.terraform-state-versioning.id == "terraform-platform-state-sandbox-test"
    error_message = "Should be: terraform-platform-state-sandbox-test"
  }

  # Ownership
  assert {
    condition     = aws_s3_bucket_ownership_controls.terraform-state-ownership.bucket == "terraform-platform-state-sandbox-test"
    error_message = "Should be: terraform-platform-state-sandbox-test"
  }

  # Public Access
  assert {
    condition     = aws_s3_bucket_public_access_block.block.bucket == aws_s3_bucket.terraform-state.id
    error_message = "Should be: terraform-platform-state-sandbox-test"
  }

  # SSE
  assert {
    condition     = aws_s3_bucket_server_side_encryption_configuration.terraform-state-sse.bucket == "terraform-platform-state-sandbox-test"
    error_message = "Should be: terraform-platform-state-sandbox-test"
  }

  # KMS Key
  assert {
    condition     = aws_kms_alias.key-alias.target_key_id == aws_kms_key.terraform-bucket-key.id
    error_message = "The KMS alias is not assigned to the correct KMS key"
  }

  assert {
    condition     = aws_kms_key.terraform-bucket-key.multi_region == false
    error_message = "Should be: false"
  }

  # Dynamo
  assert {
    condition     = aws_dynamodb_table.terraform-state.stream_enabled == false
    error_message = "Should be: false"
  }
}
