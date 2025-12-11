mock_provider "aws" {}

override_data {
  target = data.aws_caller_identity.current
  values = {
    account_id = "001122334455"
  }
}

override_data {
  target = data.aws_region.current
  values = {
    name = "eu-west-2"
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
  target = data.aws_service_discovery_dns_namespace.private_dns_namespace
  values = {
    id   = "ns-test123"
    name = "dev.demodjango.services.local"
    type = "DNS_PRIVATE"
  }
}

override_data {
  target = data.aws_iam_policy_document.assume_role
  values = {
    json = "{\"Sid\": \"PlaceholderPolicyDoesNotMatter\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.secrets
  values = {
    json = "{\"Sid\": \"PlaceholderPolicyDoesNotMatter\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.execute_command
  values = {
    json = "{\"Sid\": \"PlaceholderPolicyDoesNotMatter\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.appconfig
  values = {
    json = "{\"Sid\": \"PlaceholderPolicyDoesNotMatter\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.service_logs
  values = {
    json = "{\"Sid\": \"PlaceholderPolicyDoesNotMatter\"}"
  }
}


override_data {
  target = data.aws_ssm_parameter.log-destination-arn
  values = {
    value = "{\"dev\":\"arn:aws:logs:eu-west-2:001122334455:log-group:/central/dev\",\"prod\":\"arn:aws:logs:eu-west-2:001122334455:log-group:/central/prod\"}"
  }
}

override_data {
  target = data.aws_kms_alias.s3_key["demodjango-s3-bucket"]
  values = {
    name           = "alias/demodjango-dev-key"
    target_key_arn = "arn:aws:kms:eu-west-2:001122334455:key/aaaa-bbbb-cccc"
  }
}

variables {
  application         = "demodjango"
  environment         = "dev"
  platform_extensions = {} # Empty placeholder to pass validate - declared further down in individual tests

  env_config = {
    dev = {
      accounts = {
        deploy = { name = "sandbox", id = "000123456789" }
        dns    = { name = "dev", id = "123456" }
      }
      vpc                     = "test-vpc"
      service-deployment-mode = "doesn't matter"
    }
    hotfix = {
      accounts = {
        deploy = { name = "prod", id = "999888777666" }
        dns    = { name = "dev", id = "123456" }
      }
      vpc = "test-vpc-hotfix"
    }
  }

  service_config = {
    name = "web"
    type = "Load Balanced Web Service"

    http = {
      alias            = ["web.dev.myapp.uktrade.digital"]
      path             = "/"
      target_container = "nginx"
      healthcheck = {
        path                = "/test"
        port                = 8081
        success_codes       = "200,302"
        healthy_threshold   = 9
        unhealthy_threshold = 9
        interval            = "99"
        timeout             = "99"
        grace_period        = "99"
      }
    }

    sidecars = {
      nginx = {
        port  = 443
        image = "public.ecr.aws/example/nginx:latest"
      }
    }

    image = {
      location = "public.ecr.aws/example/app:latest"
      port     = 8080
    }

    cpu    = 256
    memory = 512
    count  = 1
    exec   = true

    network = {
      connect = true
      vpc = {
        placement = "private"
      }
    }

    storage = {
      readonly_fs          = false
      writable_directories = []
    }

    variables = {
      LOG_LEVEL = "DEBUG"
      DEBUG     = false
      PORT      = 8080
    }

    secrets = {
      DJANGO_SECRET_KEY = "/copilot/demodjango/dev/secrets/DJANGO_SECRET_KEY"
    }
  }
}



run "test_target_group_health_checks" {
  command = plan

  assert {
    condition     = aws_lb_target_group.target_group[0].health_check[0].port == "8081"
    error_message = "Should be '8081'"
  }

  assert {
    condition     = aws_lb_target_group.target_group[0].health_check[0].path == "/test"
    error_message = "Should be '/test'"
  }

  assert {
    condition     = aws_lb_target_group.target_group[0].health_check[0].matcher == "200,302"
    error_message = "Should be '200,302'"
  }

  assert {
    condition     = aws_lb_target_group.target_group[0].health_check[0].healthy_threshold == 9
    error_message = "Should be '9'"
  }

  assert {
    condition     = aws_lb_target_group.target_group[0].health_check[0].unhealthy_threshold == 9
    error_message = "Should be '9'"
  }

  assert {
    condition     = aws_lb_target_group.target_group[0].health_check[0].interval == 99
    error_message = "Should be '99'"
  }

  assert {
    condition     = aws_lb_target_group.target_group[0].health_check[0].timeout == 99
    error_message = "Should be '99'"
  }
}



run "with_custom_iam_policy" {
  command = plan

  variables {
    custom_iam_policy_json = <<EOT
{
    "Statement": [
        {
            "Action": [
                "s3:ListAllMyBuckets"
            ],
            "Effect": "Allow",
            "Resource": "*"
        }
    ],
    "Version": "2012-10-17"
}
EOT
  }

  assert {
    condition     = length(aws_iam_policy.custom_iam_policy) == 1
    error_message = "Expected 1 custom IAM policy."
  }
  assert {
    condition     = length(aws_iam_role_policy_attachment.custom_iam_policy_attachment) == 1
    error_message = "Expected 1 custom IAM policy attachments."
  }
}



run "without_custom_iam_policy" {
  command = plan

  variables {
    custom_iam_policy_json = null
  }

  assert {
    condition     = length(aws_iam_policy.custom_iam_policy) == 0
    error_message = "Not expecting any custom IAM policy to be created."
  }

  assert {
    condition     = length(aws_iam_role_policy_attachment.custom_iam_policy_attachment) == 0
    error_message = "Not expecting any custom IAM policy attachment to be created."
  }
}



run "same_account_s3_non-static" {
  command = plan

  variables {
    platform_extensions = {
      # Non-static (same-account, with KMS)
      demodjango-s3-bucket = {
        type     = "s3"
        services = ["web"]
        environments = {
          "*" = { bucket_name = "demodjango-dev" } # non-static
        }
      }
    }
  }

  assert {
    condition     = length(keys(aws_iam_policy.s3_same_account_policy)) == 1
    error_message = "Expected 1 same-account S3 policies."
  }
  assert {
    condition     = length(keys(aws_iam_role_policy_attachment.s3_same_account_policy_attachment)) == 1
    error_message = "Expected 1 same-account S3 policy attachments."
  }
}



run "same_account_s3_static" {
  command = plan

  variables {
    platform_extensions = {
      # Static (same-account, no KMS key needed, DNS-domain-style bucket name, read-only)
      demodjango-s3-bucket-static = {
        type                 = "s3"
        serve_static_content = true
        services             = ["web"]
        environments = {
          "*" = {
            bucket_name = "demodjango-dev-static"
            readonly    = true
          }
        }
      }
    }
  }

  assert {
    condition     = length(keys(aws_iam_policy.s3_same_account_policy)) == 1
    error_message = "Expected 1 same-account S3 policies."
  }
  assert {
    condition     = length(keys(aws_iam_role_policy_attachment.s3_same_account_policy_attachment)) == 1
    error_message = "Expected 1 same-account S3 policy attachments."
  }

  # No KMS statement for static buckets
  assert {
    condition = (
      length([
        for i in jsondecode(values(aws_iam_policy.s3_same_account_policy)[0].policy).Statement :
        i if i.Sid == "KMSDecryptAndGenerate"
      ]) == 0
    )
    error_message = "Policy for a static bucket should not include a KMS statements."
  }
}



run "cross_env_s3_policy" {
  command = plan

  variables {
    platform_extensions = {
      # Cross-env static bucket owned by hotfix (dev environment, web service access, read/write permissions)
      demodjango-s3-bucket-static-cross-env = {
        type                 = "s3"
        serve_static_content = true
        services             = ["web"]
        environments = {
          dev = {
            bucket_name = "demodjango-dev-static"
          }
          hotfix = {
            bucket_name = "demodjango-hotfix-static"
            cross_environment_service_access = {
              allow-dev-web-access = {
                account           = "999888777666"
                environment       = "dev"
                service           = "web"
                read              = true
                write             = true
                cyber_sign_off_by = "somebody@businessandtrade.gov.uk"
              }
            }
          }
        }
      }
    }

  }

  assert {
    condition     = length(keys(aws_iam_policy.s3_cross_env_policy)) == 1
    error_message = "Expected 1 cross-env S3 policy."
  }

  assert {
    condition     = length(keys(aws_iam_role_policy_attachment.s3_cross_env_policy_attachment)) == 1
    error_message = "Expected 1 cross-env S3 policy attachment."
  }

  # No KMS statement for static buckets
  assert {
    condition = (
      length([
        for i in jsondecode(values(aws_iam_policy.s3_cross_env_policy)[0].policy).Statement :
        i if i.Sid == "KMSDecryptAndGenerate"
      ]) == 0
    )
    error_message = "Policy for a static bucket should not include a KMS statements."
  }
}
