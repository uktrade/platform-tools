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

override_module {
  target  = module.scheduling["enabled"]
  outputs = {}
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
      location = "public.ecr.aws/example/app"
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

  scheduled_job_image_tag = null
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


run "web_service_ecs_service_connect" {
  command = plan

  variables {
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
        location = "public.ecr.aws/example/app"
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

  assert {
    condition     = aws_ecs_service.service["enabled"].service_connect_configuration[0].enabled == true
    error_message = "Should be: true"
  }

  assert {
    condition     = aws_ecs_service.service["enabled"].service_registries[0].port == 443
    error_message = "Should be: 8080"
  }
}


run "backend_service_ecs_service_connect" {
  command = plan

  variables {
    service_config = {
      name = "web"
      type = "Backend Service"

      sidecars = {
        nginx = {
          port  = 443
          image = "public.ecr.aws/example/nginx:latest"
        }
      }

      image = {
        location = "public.ecr.aws/example/app"
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

  assert {
    condition     = aws_ecs_service.service["enabled"].service_connect_configuration[0].enabled == true
    error_message = "Should be: true"
  }

  assert {
    condition     = aws_ecs_service.service["enabled"].service_registries[0].port == 8080
    error_message = "Should be: 8080"
  }
}


run "backend_service_no_ecs_service_connect" {
  command = plan

  variables {
    service_config = {
      name = "web"
      type = "Backend Service"

      sidecars = {
        nginx = {
          port  = 443
          image = "public.ecr.aws/example/nginx:latest"
        }
      }

      image = {
        location = "public.ecr.aws/example/app"
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

  assert {
    condition     = length(aws_ecs_service.service["enabled"].service_connect_configuration) == 0
    error_message = "Should be: 0"
  }

  assert {
    condition     = length(aws_ecs_service.service["enabled"].service_registries) == 0
    error_message = "Should be: 0"
  }
}

run "service_scheduled_auto_scaling" {
  command = plan

  variables {
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
        location = "public.ecr.aws/example/app"
        port     = 8080
      }

      cpu    = 256
      memory = 512
      count = {
        range = "2-8"
        schedules = [
          {
            schedule = "0 06 ? * MON-FRI *"
            range    = "2-4"
          },
          {
            schedule = "0 18 ? * MON-FRI *"
            range    = "0-0"
          },
        ]
      }
      exec = true

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

  assert {
    condition     = length(aws_appautoscaling_scheduled_action.scheduled_autoscaling) == 2
    error_message = "Should be: 2"
  }

  assert {
    condition     = aws_appautoscaling_scheduled_action.scheduled_autoscaling["demodjango-dev-web-schedule-0"].schedule == "cron(0 06 ? * MON-FRI *)"
    error_message = "Should be: cron(0 06 ? * MON-FRI *)"
  }

  assert {
    condition     = aws_appautoscaling_scheduled_action.scheduled_autoscaling["demodjango-dev-web-schedule-0"].scalable_target_action[0].min_capacity == "2"
    error_message = "Should be: 2"
  }

  assert {
    condition     = aws_appautoscaling_scheduled_action.scheduled_autoscaling["demodjango-dev-web-schedule-0"].scalable_target_action[0].max_capacity == "4"
    error_message = "Should be: 4"
  }

  assert {
    condition     = aws_appautoscaling_scheduled_action.scheduled_autoscaling["demodjango-dev-web-schedule-1"].schedule == "cron(0 18 ? * MON-FRI *)"
    error_message = "Should be: cron(0 18 ? * MON-FRI *)"
  }

  assert {
    condition     = aws_appautoscaling_scheduled_action.scheduled_autoscaling["demodjango-dev-web-schedule-1"].scalable_target_action[0].min_capacity == "0"
    error_message = "Should be: 0"
  }

  assert {
    condition     = aws_appautoscaling_scheduled_action.scheduled_autoscaling["demodjango-dev-web-schedule-1"].scalable_target_action[0].max_capacity == "0"
    error_message = "Should be: 0"
  }
}

run "test_scheduling_module_is_created_for_scheduled_job" {
  command = plan

  variables {
    service_config = {
      name = "web"
      type = "Scheduled Job"

      image = {
        location = "public.ecr.aws/example/app"
        port     = 8080
      }

      cpu    = 256
      memory = 512

      exec      = true
      essential = true

      schedule = "none"
      timeout  = 300

      storage = {
        readonly_fs          = false
        writable_directories = []
      }
    }

    scheduled_job_image_tag = "some-tag"

  }

  assert {
    condition     = length(module.scheduling) == 1
    error_message = "Should create the scheduling module"
  }
}

run "test_scheduling_module_is_not_created_for_load_balanced_web_service" {
  command = plan

  assert {
    condition     = length(module.scheduling) == 0
    error_message = "Should not create the scheduling module"
  }
}

run "test_conditionally_creates_resources_for_a_scheduled_job" {
  command = plan

  variables {
    service_config = {
      name = "web"
      type = "Scheduled Job"

      image = {
        location = "public.ecr.aws/example/app"
        port     = 8080
      }

      cpu       = 256
      memory    = 512
      exec      = true
      essential = true

      schedule = "none"
      timeout  = 300

      storage = {
        readonly_fs          = false
        writable_directories = []
      }
    }

    scheduled_job_image_tag = "some-tag"
  }

  assert {
    condition     = length(aws_ecs_service.service) == 0
    error_message = "Should not create the ecs service for a scheduled job"
  }

  assert {
    condition     = length(aws_lambda_invocation.dummy_listener_rule) == 0
    error_message = "Should not create a lambda invocation for a scheduled job"
  }

  assert {
    condition     = length(aws_ecs_task_definition.default_task_def) == 0
    error_message = "Should not create a default task definition for a scheduled job"
  }

  assert {
    condition     = length(aws_s3_object.task_definition) == 0
    error_message = "Should not create the s3 bucket for a scheduled job"
  }

  assert {
    condition     = length(aws_appautoscaling_target.ecs_autoscaling) == 0
    error_message = "Should not create the app autoscaling target for a scheduled job"
  }

  assert {
    condition     = length(aws_appautoscaling_scheduled_action.scheduled_autoscaling) == 0
    error_message = "Should not create the app autoscaling target for a scheduled job"
  }

  assert {
    condition     = length(aws_lb_target_group.target_group) == 0
    error_message = "Should not create a load balancer target group for a scheduled job"
  }

  assert {
    condition     = length(data.aws_service_discovery_dns_namespace.private_dns_namespace) == 0
    error_message = "Should not create service discovery resources for a scheduled job"
  }

  assert {
    condition     = length(aws_service_discovery_service.service_discovery_service) == 0
    error_message = "Should not create service discovery resources for a scheduled job"
  }

  assert {
    condition     = length(aws_appautoscaling_policy.cpu_autoscaling_policy) == 0
    error_message = "Should not create autoscaling policy for a scheduled job"
  }

  assert {
    condition     = length(aws_appautoscaling_policy.memory_autoscaling_policy) == 0
    error_message = "Should not create autoscaling memory policy for a scheduled job"
  }

  assert {
    condition     = length(data.aws_lb.load_balancer) == 0
    error_message = "Should not load load balancer data for a scheduled job"
  }

  assert {
    condition     = length(aws_appautoscaling_policy.requests_autoscaling_policy) == 0
    error_message = "Should not create autoscaling requests policy for a scheduled job"
  }

  assert {
    condition     = length(aws_ecs_task_definition.scheduled_job) == 1
    error_message = "Should create task definition for a scheduled job"
  }
}


# Write a test to check the default values for retries and timeout (already exists in the old module tests we think)

run "test_ecs_task_default_platform_is_x86_64" {
  command = plan
  variables {
    service_config = {
      name = "web"
      type = "Scheduled Job"

      image = {
        location = "public.ecr.aws/example/app"
        port     = 8080
      }

      cpu    = 256
      memory = 512

      exec      = true
      essential = true

      schedule = "none"
      timeout  = 300

      storage = {
        readonly_fs          = false
        writable_directories = []
      }
    }

    scheduled_job_image_tag = "some-tag"
  }

  assert {
    condition     = local.cpu_architecture == "X86_64"
    error_message = "Should be 'X86_64'"
  }
}

run "test_ecs_task_platform_is_arm64" {
  command = plan

  variables {
    service_config = merge(var.service_config, { platform = "arm64" })
  }

  assert {
    condition     = local.cpu_architecture == "ARM64"
    error_message = "Should be 'ARM64'"
  }
}

run "test_scheduled_job_requires_image_tag_variable" {
  command = plan
  variables {
    service_config = {
      name = "web"
      type = "Scheduled Job"

      image = {
        location = "public.ecr.aws/example/app"
        port     = 8080
      }

      cpu    = 256
      memory = 512

      exec      = true
      essential = true

      schedule = "none"
      timeout  = 300

      storage = {
        readonly_fs          = false
        writable_directories = []
      }
    }
  }

  expect_failures = [var.scheduled_job_image_tag]
}

run "test_non_scheduled_job_service_does_not_require_image_tag_variable" {
  command = plan
  variables {
    scheduled_job_image_tag = "some-tag"
  }

  expect_failures = [var.scheduled_job_image_tag]
}


override_data {
  target = data.aws_acm_certificate.acm
  values = {
    status = "PENDING_VALIDATION"
    arn    = "arn:aws:acm:eu-west-2:123456789012:certificate/xxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx"
  }
}

override_data {
  target = data.aws_lb.nlb
  values = {
    arn = "arn:aws:elasticloadbalancing:eu-west-2:123456789012:loadbalancer/net/demodjango-dev-nlb/xxxx"
  }
}

run "internal_service" {
  command = plan

  variables {
    service_config = {
      name = "internal"
      type = "Load Balanced Internal Service"

      http = {
        alias            = ["internal.dev.myapp.uktrade.digital"]
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
        location = "public.ecr.aws/example/app"
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

  assert {
    condition     = contains(aws_ecs_service.service["enabled"].load_balancer[*].container_port, 443)
    error_message = "Should be: 443"
  }

  assert {
    condition     = aws_lb_listener.nlb["internal.dev.myapp.uktrade.digital"].load_balancer_arn == "arn:aws:elasticloadbalancing:eu-west-2:123456789012:loadbalancer/net/demodjango-dev-nlb/xxxx"
    error_message = "Should be: arn:aws:elasticloadbalancing:eu-west-2:123456789012:loadbalancer/net/demodjango-dev-nlb/xxxx"
  }

  assert {
    condition     = aws_lb_listener.nlb["internal.dev.myapp.uktrade.digital"].certificate_arn == "arn:aws:acm:eu-west-2:123456789012:certificate/xxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx"
    error_message = "Should be: arn:aws:acm:eu-west-2:123456789012:certificate/xxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx"
  }

  assert {
    condition     = aws_lb_target_group.nlb_to_ecs[0].protocol == "TLS"
    error_message = "Should be: TLS"
  }
  assert {
    condition     = aws_acm_certificate_validation.private-cert-validation["internal.dev.myapp.uktrade.digital"].certificate_arn == "arn:aws:acm:eu-west-2:123456789012:certificate/xxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx"
    error_message = "Should be: arn:aws:acm:eu-west-2:123456789012:certificate/xxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx"
  }
}