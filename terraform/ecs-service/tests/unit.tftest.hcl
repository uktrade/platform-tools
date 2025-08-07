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
    name = "dev.demodjango.services.local"
    type = "DNS_PRIVATE"
  }
}

override_data {
  target = data.aws_iam_policy_document.assume_role_policy
  values = {
    json = <<EOT
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      }
    }
  ]
}
EOT
  }
}

override_data {
  target = data.aws_iam_policy_document.secrets_policy
  values = {
    json = <<EOT
{
    "Statement": [
        {
            "Action": "secretsmanager:GetSecretValue",
            "Condition": {
                "StringEquals": {
                    "aws:ResourceTag/copilot-application": "demodjango",
                    "ssm:ResourceTag/copilot-environment": "dev"
                }
            },
            "Effect": "Allow",
            "Resource": "arn:aws:secretsmanager:eu-west-2:001122334455:secret:*"
        },
        {
            "Action": "kms:Decrypt",
            "Effect": "Allow",
            "Resource": "arn:aws:kms:eu-west-2:001122334455:key/*"
        },
        {
            "Action": "kms:Decrypt",
            "Condition": {
                "StringEquals": {
                    "aws:ResourceTag/copilot-application": "demodjango",
                    "ssm:ResourceTag/copilot-environment": "dev"
                }
            },
            "Effect": "Allow",
            "Resource": "arn:aws:kms:eu-west-2:001122334455:key/*"
        },
        {
            "Action": "ssm:GetParameters",
            "Condition": {
                "StringEquals": {
                    "aws:ResourceTag/copilot-application": "demodjango",
                    "ssm:ResourceTag/copilot-environment": "dev"
                }
            },
            "Effect": "Allow",
            "Resource": "arn:aws:ssm:eu-west-2:001122334455:parameter/*"
        },
        {
            "Action": "ssm:GetParameters",
            "Condition": {
                "StringEquals": {
                    "aws:ResourceTag/copilot-application": "__all__"
                }
            },
            "Effect": "Allow",
            "Resource": "arn:aws:ssm:eu-west-2:001122334455:parameter/*"
        }
    ],
    "Version": "2012-10-17"
}
EOT
  }
}

override_data {
  target = data.aws_iam_policy_document.execute_command_policy
  values = {
    json = <<EOT
{
    "Statement": [
        {
            "Action": [
                "ssmmessages:OpenDataChannel",
                "ssmmessages:OpenControlChannel",
                "ssmmessages:CreateDataChannel",
                "ssmmessages:CreateControlChannel"
            ],
            "Effect": "Allow",
            "Resource": "*"
        },
        {
            "Action": [
                "logs:PutLogEvents",
                "logs:DescribeLogStreams",
                "logs:DescribeLogGroups",
                "logs:CreateLogStream"
            ],
            "Effect": "Allow",
            "Resource": "*"
        },
        {
            "Action": "iam:*",
            "Effect": "Deny",
            "Resource": "*"
        },
        {
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Resource": "arn:aws:iam::1234567890:role/AppConfigIpFilterRole"
        },
        {
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Resource": "arn:aws:iam::0987654321:role/amp-prometheus-role"
        }
    ],
    "Version": "2012-10-17"
}
EOT
  }
}

variables {
  application = "demodjango"
  environment = "dev"

  env_config = {
    "dev" = {
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

  service_config = {
    name = "web"
    type = "Load Balanced Web Service"

    http = {
      path             = "/"
      target_container = "nginx"
      healthcheck = {
        path                = "/test"
        port                = 8081
        success_codes       = "200,302"
        healthy_threshold   = 9
        unhealthy_threshold = 9
        interval            = "99s"
        timeout             = "99s"
        grace_period        = "99s"
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
      readonly_fs = false
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