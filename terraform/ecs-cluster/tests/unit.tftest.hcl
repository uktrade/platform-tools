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
  target = data.aws_ip_ranges.service_ranges["3"]
  values = {
    cidr_blocks = ["23.20.0.0/14", "23.24.0.0/14"]
    services    = ["CLOUDFRONT"]
    regions     = ["eu-west-2"]
  }
}

override_data {
  target = data.aws_ip_ranges.service_ranges["4"]
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
    error_message = "Egress does not exist."
  }

  assert {
    condition     = toset(tolist(aws_security_group.environment_security_group.egress)[0].cidr_blocks) == toset(["0.0.0.0/0"])
    error_message = "egress does not include the default cidr range."
  }

  assert {
    condition     = tolist(aws_security_group.environment_security_group.egress)[0].protocol == "-1"
    error_message = "egress protocol is not as expected."
  }

  assert {
    condition     = tolist(aws_security_group.environment_security_group.egress)[0].to_port == 0
    error_message = "egress to_port is not as expected."
  }

  assert {
    condition     = tolist(aws_security_group.environment_security_group.egress)[0].from_port == 0
    error_message = "egress from_port is not as expected."
  }

  assert {
    condition     = length(aws_vpc_security_group_ingress_rule.vpc_endpoints) == 0
    error_message = "expected aws_vpc_security_group_ingress_rule.vpc_endpoints not to be created"
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
    egress_rules = [
      {
        to = {
          cidr_blocks = ["172.65.64.208/30"]
        }
        protocol  = "tcp"
        from_port = 443
        to_port   = 443
      },
      {
        to = {
          cidr_blocks = ["15.200.117.191/32", "172.65.64.208/30"]
        }
        protocol  = "udp"
        from_port = 7000
        to_port   = 7010
      },
      {
        to = {
          vpc_endpoints = true
        }
        protocol  = "tcp"
        from_port = 443
        to_port   = 443
      },
      {
        to = {
          aws_cidr_blocks = {
            services = ["CLOUDFRONT"]
            regions  = ["eu-west-2"]
          }
        }
        protocol  = "tcp"
        from_port = 443
        to_port   = 443
      },
      {
        to = {
          aws_cidr_blocks = {
            services = ["EC2"]
            regions  = ["GLOBAL"]
          }
        }
        protocol  = "tcp"
        from_port = 80
        to_port   = 80
      }
    ]

  }

  assert {
    condition = tomap({
      for block in aws_security_group.environment_security_group.egress :
      block.description => toset(block.cidr_blocks)
      }) == tomap({
      "Egress rule 0" = toset(["172.65.64.208/30"])
      "Egress rule 1" = toset(["15.200.117.191/32", "172.65.64.208/30"])
      "Egress rule 2" = null
      "Egress rule 3" = toset(["23.20.0.0/14", "23.24.0.0/14"])
      "Egress rule 4" = toset(["56.20.0.0/14", "56.24.0.0/14"])
    })
    error_message = "Egress cidr_blocks attributes are not as expected."
  }

  assert {
    condition = tomap({
      for block in aws_security_group.environment_security_group.egress :
      block.description => toset(block.security_groups)
      }) == tomap({
      "Egress rule 0" = null
      "Egress rule 1" = null
      "Egress rule 2" = toset(["vpce-security-group-id"])
      "Egress rule 3" = null
      "Egress rule 4" = null
    })
    error_message = "Egress security_groups attributes are not as expected."
  }

  assert {
    condition = {
      for block in aws_security_group.environment_security_group.egress :
      block.description => block.protocol
      } == {
      "Egress rule 0" = "tcp"
      "Egress rule 1" = "udp"
      "Egress rule 2" = "tcp"
      "Egress rule 3" = "tcp"
      "Egress rule 4" = "tcp"
    }
    error_message = "Egress protocol attributes are not as expected."
  }

  assert {
    condition = {
      for block in aws_security_group.environment_security_group.egress :
      block.description => block.from_port
      } == {
      "Egress rule 0" = 443
      "Egress rule 1" = 7000
      "Egress rule 2" = 443
      "Egress rule 3" = 443
      "Egress rule 4" = 80
    }
    error_message = "Egress from_port attributes are not as expected."
  }

  assert {
    condition = {
      for block in aws_security_group.environment_security_group.egress :
      block.description => block.to_port
      } == {
      "Egress rule 0" = 443
      "Egress rule 1" = 7010
      "Egress rule 2" = 443
      "Egress rule 3" = 443
      "Egress rule 4" = 80
    }
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
    error_message = "aws ip ranges data source should be created"
  }

  assert {
    condition     = contains(data.aws_ip_ranges.service_ranges["3"].services, "CLOUDFRONT")
    error_message = "Data source should include CLOUDFRONT service."
  }

  assert {
    condition     = contains(data.aws_ip_ranges.service_ranges["3"].regions, "eu-west-2")
    error_message = "Data source should include eu-west-2 region."
  }

  assert {
    condition     = contains(data.aws_ip_ranges.service_ranges["4"].services, "EC2")
    error_message = "Data source should include EC2 service."
  }

  assert {
    condition     = contains(data.aws_ip_ranges.service_ranges["4"].regions, "GLOBAL")
    error_message = "Data source should include GLOBAL region."
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
    egress_rules = [
      {
        to        = {}
        protocol  = "tcp"
        from_port = 443
        to_port   = 443
      }
    ]
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
    egress_rules = [
      {
        to = {
          cidr_blocks   = ["15.200.117.191/32", "172.65.64.208/30"]
          vpc_endpoints = true
        }
        protocol  = "tcp"
        from_port = 443
        to_port   = 443
      },
    ]
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
    egress_rules = [
      {
        to = {
          cidr_blocks = ["15.200.117.191/32", "172.65.64.208/30"]
          aws_cidr_blocks = {
            services = ["CLOUDFRONT"]
            regions  = ["eu-west-2"]
          }
        }
        protocol  = "tcp"
        from_port = 443
        to_port   = 443
      },
    ]
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

