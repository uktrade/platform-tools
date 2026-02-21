variables {
  vpc_name       = "s3-test-vpc-name"
  application    = "s3-test-application"
  environment    = "s3-test-environment"
  name           = "s3-test-name"
  cdn_account_id = "0123456789"
  
  config = {
    "bucket_name" = "dbt-terraform-test-s3-module",
    "type"        = "string",
    "versioning"  = false,
    "objects"     = [],
    "lifecycle_rules" = [{
      "filter_prefix"   = "test-prefix",
      "expiration_days" = 99,
      "enabled"         = true
    }]
  }
}

mock_provider "aws" {
  alias = "domain-cdn"
}

mock_provider "aws" {
  alias = "domain"
}

run "aws_s3_bucket_e2e_test" {
  command = apply

  assert {
    condition     = [for el in aws_s3_bucket.this.grant : true if[for el2 in el.permissions : true if el2 == "FULL_CONTROL"][0]][0] == true
    error_message = "Should be: FULL_CONTROL"
  }

  assert {
    condition     = aws_s3_bucket.this.object_lock_enabled == false
    error_message = "Should be: false"
  }
}

run "aws_kms_key_e2e_test" {
  command = apply

  assert {
    condition     = startswith(aws_kms_key.kms-key[0].arn, "arn:aws:kms:eu-west-2:${data.aws_caller_identity.current.account_id}") == true
    error_message = "Should be: arn:aws:kms:eu-west-2:${data.aws_caller_identity.current.account_id}"
  }
}

run "aws_s3_bucket_policy_e2e_test" {
  command = apply

  assert {
    condition     = aws_s3_bucket_policy.bucket-policy[0].bucket == "dbt-terraform-test-s3-module"
    error_message = "Should be: dbt-terraform-test-s3-module"
  }

  assert {
    condition     = jsondecode(aws_s3_bucket_policy.bucket-policy[0].policy).Statement[0].Effect == "Deny"
    error_message = "Should be: Deny"
  }

  assert {
    condition     = [for el in jsondecode(aws_s3_bucket_policy.bucket-policy[0].policy).Statement[0].Condition : false if[for el2 in el : true if el2 == "false"][0]][0] == false
    error_message = "Should be: aws:SecureTransport"
  }

  assert {
    condition     = jsondecode(aws_s3_bucket_policy.bucket-policy[0].policy).Statement[0].Action == "s3:*"
    error_message = "Should be: s3:*"
  }
}

run "aws_s3_bucket_lifecycle_configuration_e2e_test" {
  command = apply

  assert {
    condition     = aws_s3_bucket_lifecycle_configuration.lifecycle-configuration[0].rule[0].abort_incomplete_multipart_upload[0].days_after_initiation == 7
    error_message = "Should be: 7 days for aborting incomplete uploads"
  }

  assert {
    condition     = aws_s3_bucket_lifecycle_configuration.lifecycle-configuration[0].rule[0].filter[0].prefix == "test-prefix"
    error_message = "Should be: empty prefix"
  }

  assert {
    condition     = aws_s3_bucket_lifecycle_configuration.lifecycle-configuration[0].rule[0].expiration[0].days == 99
    error_message = "Should be: 99 days for expiration"
  }

  assert {
    condition     = aws_s3_bucket_lifecycle_configuration.lifecycle-configuration[0].rule[0].status == "Enabled"
    error_message = "Should be: status Enabled"
  }
}

run "aws_kms_alias_e2e_test" {
  command = apply

  assert {
    condition     = aws_kms_alias.s3-bucket[0].name == "alias/s3-test-application-s3-test-environment-dbt-terraform-test-s3-module-key"
    error_message = "Should be: alias/s3-test-application-s3-test-environment-dbt-terraform-test-s3-module-key"
  }
}

run "aws_s3_object_e2e_test" {
  command = apply

  variables {
    config = {
      "bucket_name" = "dbt-terraform-test-s3-module",
      "type"        = "string",
      "versioning"  = true,
      "objects"     = [{ "key" = "local_file", "body" = "./tests/test_files/local_file.txt" }],
    }
  }

  assert {
    condition     = aws_s3_object.object["local_file"].arn == "arn:aws:s3:::dbt-terraform-test-s3-module/local_file"
    error_message = "Invalid S3 object arn"
  }

  assert {
    condition     = aws_s3_object.object["local_file"].kms_key_id == "arn:aws:kms:eu-west-2:${data.aws_caller_identity.current.account_id}:key/${aws_kms_key.kms-key[0].id}"
    error_message = "Invalid kms key id"
  }

  assert {
    condition     = aws_s3_object.object["local_file"].server_side_encryption == "aws:kms"
    error_message = "Invalid S3 object etag"
  }
}

# run "aws_cloudfront_distribution_e2e_test" {
#   command = apply

#   variables {
#     vpc_name    = "s3-test-vpc-name"
#     application = "s3-test-application"
#     environment = "s3-test-environment"
#     name        = "s3-test-name"
#     config = {
#       "bucket_name" = "test",
#       "type"        = "string",
#       "versioning"  = false,
#       "objects"     = [],
#       "serve_static_content" = true,
#       "lifecycle_rules" = [{
#           "filter_prefix" = "test-prefix",
#           "expiration_days" = 99,
#           "enabled"       = true
#         }]
#     }
# }

#   assert {
#     condition     = aws_cloudfront_distribution.s3_distribution[0].viewer_certificate[0].acm_certificate_arn == aws_acm_certificate.certificate[0].arn
#     error_message = "Should match the ACM certificate ARN"
#   }

# }
