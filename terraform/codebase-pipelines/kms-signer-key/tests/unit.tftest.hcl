mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "000123456789" # mock non-prod account
    }
  }
}


variables {
    application = "test-app"
    deploy_account_ids = ["000123456789", "111234567890"]
    static_signer_alias = "test-alias"
    key_alias_mappings = {
      "v_test" = {
        "alias" = "alias/test"
        "description" = "test-description"
      }
    }
    tags = {
      Name = "test-tag"
    }
  }

run "test_creation_of_single_kms_key" {
  command = plan
  
  assert {
    condition     = aws_kms_key.container_image_signer_key["v_test"] != null
    error_message = "A single KMS Key should have been created"
  }

  assert {
    condition     = length(jsondecode(aws_kms_key.container_image_signer_key["v_test"].policy).Statement) == 2
    error_message = "The KMS key policy should have only 2 policy statements"
  }
  assert {
    condition     = jsondecode(aws_kms_key.container_image_signer_key["v_test"].policy).Statement[0].Sid == "Allow verifying with the key"
    error_message = "First statement is expected to be the verify permissions"
  }

  assert {
    condition     = !contains(jsondecode(aws_kms_key.container_image_signer_key["v_test"].policy).Statement[0].Principal.AWS, "*")
    error_message = "A KMS key verify principal should not have wildcards"
  }

  assert {
    condition     = jsondecode(aws_kms_key.container_image_signer_key["v_test"].policy).Statement[1].Sid == "Allow signing with the key"
    error_message = "Second statement is expected to be the sign permissions"
  }

  assert {
    condition     = jsondecode(aws_kms_key.container_image_signer_key["v_test"].policy).Statement[1].Principal.AWS == "arn:aws:iam::000123456789:role/github-oidc-build-placeholder-role"
    error_message = "A KMS key sign principal should be the build oidc role in the non-prod (build and deploy) account ONLY"
  }

  assert {
    condition     = aws_kms_alias.container_image_signer_key["v_test"].name == "alias/test"
    error_message = "An alias for the KMS key must exist with immutable name 'alias/test'.  Changing this name would break deployments"
  }

  # Can't do the below assertion since the target_key_id is not know at plan
  # assert {
  #   condition     = aws_kms_alias.container_image_signer_key.target_key_id == aws_kms_key.container_image_signer_key.id
  #   error_message = "'alias/my-app-container-image-signer-key' must point to the container image signer key"
  # }
}

