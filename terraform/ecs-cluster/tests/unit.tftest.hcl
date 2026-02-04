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
  target = data.aws_ip_ranges.service_ranges["aws1"]
  values = {
    cidr_blocks = ["23.20.0.0/14", "23.24.0.0/14"]
    services    = ["CLOUDFRONT"]
    regions     = ["eu-west-2"]
  }
}

override_data {
  target = data.aws_ip_ranges.service_ranges["aws2"]
  values = {
    cidr_blocks = ["56.20.0.0/14", "56.24.0.0/14"]
    services    = ["EC2"]
    regions     = ["GLOBAL"]
  }
}

override_data {
  target = data.aws_vpc.vpc
  values = {
    id         = "vpc-00112233aabbccdef"
    cidr_block = "10.0.0.0/16"
  }
}

run "test_create_ecs_cluster" {
  command = plan

  variables {
    application                     = "demodjango"
    environment                     = "dev"
    vpc_name                        = "terraform-tests-vpc"
    alb_https_security_group_id     = "security-group-id"
    has_vpc_endpoints               = false
    vpc_endpoints_security_group_id = null
    egress_rules                    = null
  }

  assert {
    condition     = aws_ecs_cluster.cluster.name == "demodjango-dev-cluster"
    error_message = "Cluster name should be: 'demodjango-dev-cluster'"
  }

  assert {
    condition     = aws_ecs_cluster.cluster.tags.application == "demodjango"
    error_message = "application tag was not as expected"
  }

  assert {
    condition     = aws_ecs_cluster.cluster.tags.environment == "dev"
    error_message = "environment tag was not as expected"
  }

  assert {
    condition     = aws_ecs_cluster.cluster.tags.managed-by == "DBT Platform - Environment Terraform"
    error_message = "managed-by tag was not as expected"
  }

  assert {
    condition     = aws_ecs_cluster_capacity_providers.capacity.cluster_name == "demodjango-dev-cluster"
    error_message = "Cluster name for capacity provider should be: 'demodjango-dev-cluster'"
  }

  assert {
    condition     = aws_security_group.environment_security_group.tags.Name == "platform-demodjango-dev-env-sg"
    error_message = "Name tag was not as expected"
  }

  assert {
    condition     = length(aws_security_group.environment_security_group.ingress) == 2
    error_message = "Ingress does not include enough groups."
  }
  assert {
    condition     = tolist(aws_security_group.environment_security_group.ingress)[0].security_groups == toset(["security-group-id"])
    error_message = "Ingress does not include the passed in security group id."
  }

  assert {
    condition     = length(aws_security_group.environment_security_group.egress) == 1
    error_message = "Security group should have precisely one egress block"
  }

  assert {
    condition     = toset(tolist(aws_security_group.environment_security_group.egress)[0].cidr_blocks) == toset(["0.0.0.0/0"])
    error_message = "Egress block cidr range should be \"0.0.0.0/0\""
  }

  assert {
    condition     = tolist(aws_security_group.environment_security_group.egress)[0].protocol == "-1"
    error_message = "Egress block protocol should be \"-1\""
  }

  assert {
    condition     = tolist(aws_security_group.environment_security_group.egress)[0].to_port == 0
    error_message = "Egress block to_port should be 0"
  }

  assert {
    condition     = tolist(aws_security_group.environment_security_group.egress)[0].from_port == 0
    error_message = "Egress block from_port should be 0"
  }

  assert {
    condition     = length(aws_vpc_security_group_ingress_rule.vpc_endpoints) == 0
    error_message = "Expected aws_vpc_security_group_ingress_rule.vpc_endpoints not to be created"
  }
}

run "test_create_ecs_cluster_with_egress_rules" {
  command = plan

  variables {
    application                     = "demodjango"
    environment                     = "dev"
    vpc_name                        = "terraform-tests-vpc"
    alb_https_security_group_id     = "security-group-id"
    has_vpc_endpoints               = true
    vpc_endpoints_security_group_id = "vpce-security-group-id"
    egress_rules = {
      cidrs1 = {
        destination = {
          cidr_blocks = ["172.65.64.208/30"]
        }
        protocol  = "tcp"
        from_port = 443
        to_port   = 443
      }
      cidrs2 = {
        destination = {
          cidr_blocks = ["15.200.117.191/32", "172.65.64.208/30"]
        }
        protocol  = "udp"
        from_port = 7000
        to_port   = 7010
      }
      vpce = {
        destination = {
          vpc_endpoints = true
        }
        protocol  = "tcp"
        from_port = 443
        to_port   = 443
      }
      aws1 = {
        destination = {
          aws_cidr_blocks = {
            services = ["CLOUDFRONT"]
            regions  = ["eu-west-2"]
          }
        }
        protocol  = "tcp"
        from_port = 443
        to_port   = 443
      }
      aws2 = {
        destination = {
          aws_cidr_blocks = {
            services = ["EC2"]
            regions  = ["GLOBAL"]
          }
        }
        protocol  = "all"
        from_port = 80
        to_port   = 80
      }
    }
  }

  assert {
    condition = tomap({
      for block in aws_security_group.environment_security_group.egress :
      block.description => toset(block.cidr_blocks)
      }) == tomap({
      "Egress: cidrs1" = toset(["172.65.64.208/30"])
      "Egress: cidrs2" = toset(["15.200.117.191/32", "172.65.64.208/30"])
      "Egress: vpce"   = null
      "Egress: aws1"   = toset(["23.20.0.0/14", "23.24.0.0/14"])
      "Egress: aws2"   = toset(["56.20.0.0/14", "56.24.0.0/14"])
    })
    error_message = "Egress cidr_blocks attributes are not as expected."
  }

  assert {
    condition = tomap({
      for block in aws_security_group.environment_security_group.egress :
      block.description => toset(block.security_groups)
      }) == tomap({
      "Egress: cidrs1" = null
      "Egress: cidrs2" = null
      "Egress: vpce"   = toset(["vpce-security-group-id"])
      "Egress: aws1"   = null
      "Egress: aws2"   = null
    })
    error_message = "Egress security_groups attributes are not as expected."
  }

  assert {
    condition = tomap({
      for block in aws_security_group.environment_security_group.egress :
      block.description => block.protocol
      }) == tomap({
      "Egress: cidrs1" = "tcp"
      "Egress: cidrs2" = "udp"
      "Egress: vpce"   = "tcp"
      "Egress: aws1"   = "tcp"
      "Egress: aws2"   = "-1"
    })
    error_message = "Egress protocol attributes are not as expected."
  }

  assert {
    condition = tomap({
      for block in aws_security_group.environment_security_group.egress :
      block.description => block.from_port
      }) == tomap({
      "Egress: cidrs1" = 443
      "Egress: cidrs2" = 7000
      "Egress: vpce"   = 443
      "Egress: aws1"   = 443
      "Egress: aws2"   = 80
    })
    error_message = "Egress from_port attributes are not as expected."
  }

  assert {
    condition = tomap({
      for block in aws_security_group.environment_security_group.egress :
      block.description => block.to_port
      }) == tomap({
      "Egress: cidrs1" = 443
      "Egress: cidrs2" = 7010
      "Egress: vpce"   = 443
      "Egress: aws1"   = 443
      "Egress: aws2"   = 80
    })
    error_message = "Egress to_port attributes are not as expected."
  }

  assert {
    condition     = length(aws_security_group.environment_security_group.egress) == 5
    error_message = "Wrong number of egress blocks."
  }

  assert {
    condition     = length(aws_vpc_security_group_ingress_rule.vpc_endpoints) == 1
    error_message = "expected aws_vpc_security_group_ingress_rule.vpc_endpoints to be created"
  }

  assert {
    condition     = aws_vpc_security_group_ingress_rule.vpc_endpoints[0].security_group_id == "vpce-security-group-id"
    error_message = "aws_vpc_security_group_ingress_rule security_group_id is not as expected"
  }

  assert {
    condition     = length(data.aws_ip_ranges.service_ranges) == 2
    error_message = "Expected two instances of data.aws_ip_ranges.service_ranges"
  }
}

run "test_create_ecs_cluster_with_egress_rule_without_any_destination" {
  command = plan

  variables {
    application                     = "demodjango"
    environment                     = "dev"
    vpc_name                        = "terraform-tests-vpc"
    alb_https_security_group_id     = "security-group-id"
    has_vpc_endpoints               = true
    vpc_endpoints_security_group_id = "vpce-security-group-id"
    egress_rules = {
      myrule = {
        destination = {}
        protocol    = "tcp"
        from_port   = 443
        to_port     = 443
      }
    }
  }

  expect_failures = [var.egress_rules]
}

run "test_create_ecs_cluster_with_egress_rule_with_cidr_blocks_and_vpc_endpoints" {
  command = plan

  variables {
    application                     = "demodjango"
    environment                     = "dev"
    vpc_name                        = "terraform-tests-vpc"
    alb_https_security_group_id     = "security-group-id"
    vpc_endpoints_security_group_id = "vpce-security-group-id"
    egress_rules = {
      myrule = {
        destination = {
          cidr_blocks   = ["15.200.117.191/32", "172.65.64.208/30"]
          vpc_endpoints = true
        }
        protocol  = "tcp"
        from_port = 443
        to_port   = 443
      }
    }
  }

  expect_failures = [var.egress_rules]
}

run "test_create_ecs_cluster_with_egress_rule_with_cidr_blocks_and_aws_cidr_blocks" {
  command = plan

  variables {
    application                     = "demodjango"
    environment                     = "dev"
    vpc_name                        = "terraform-tests-vpc"
    alb_https_security_group_id     = "security-group-id"
    has_vpc_endpoints               = true
    vpc_endpoints_security_group_id = "vpce-security-group-id"
    egress_rules = {
      myrule = {
        destination = {
          cidr_blocks = ["15.200.117.191/32", "172.65.64.208/30"]
          aws_cidr_blocks = {
            services = ["CLOUDFRONT"]
            regions  = ["eu-west-2"]
          }
        }
        protocol  = "tcp"
        from_port = 443
        to_port   = 443
      }
    }
  }

  expect_failures = [var.egress_rules]
}

run "test_create_ecs_cluster_without_an_alb" {
  command = plan

  variables {
    application                     = "demodjango"
    environment                     = "dev"
    vpc_name                        = "terraform-tests-vpc"
    alb_https_security_group_id     = null
    has_vpc_endpoints               = false
    vpc_endpoints_security_group_id = null
  }

  assert {
    condition     = length(aws_security_group.environment_security_group.ingress) == 1
    error_message = "Ingress includes more than containers in the same security group."
  }
}

run "test_create_vpc_peering_ingress_rule_if_param_is_present" {
  command = plan

  variables {
    application = "demodjango"
    environment = "dev"
    vpc_name    = "terraform-tests-vpc"
  }

  override_data {
    target = data.aws_ssm_parameters_by_path.vpc_peering

    values = {
      names = [
        "/platform/vpc-peering/demodjango/dev/source-vpc/application-a-vpc/security-group/sg-abc123",
        "/platform/vpc-peering/demodjango/dev/source-vpc/application-b-vpc/security-group/sg-abc123",
        "/platform/vpc-peering/demodjango/staging/source-vpc/application-b-vpc/security-group/sg-def456" # Not this environment's security group
      ]
      values = [
        "{\"security-group-id\":\"sg-abc123\",\"port\":8080,\"application\":\"demodjango\",\"environment\":\"dev\",\"source-vpc-name\":\"application-a-vpc\",\"source-vpc-cidr\":\"10.0.0.0/16\"}",
        "{\"security-group-id\":\"sg-abc123\",\"port\":8080,\"application\":\"demodjango\",\"environment\":\"dev\",\"source-vpc-name\":\"application-b-vpc\",\"source-vpc-cidr\":\"10.1.0.0/16\"}",
        "{\"security-group-id\":\"sg-def456\",\"port\":443,\"application\":\"demodjango\",\"environment\":\"staging\",\"source-vpc-name\":\"application-c-vpc\",\"source-vpc-cidr\":\"10.2.0.0/16\"}",
      ]
    }
  }

  assert {
    condition     = length(aws_vpc_security_group_ingress_rule.vpc_peering) == 2
    error_message = "Expected 2 ingress rules, didn't get that."
  }
}
