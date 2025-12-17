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

run "test_create_ecs_cluster" {
  command = plan

  variables {
    application                     = "demodjango"
    environment                     = "dev"
    vpc_name                        = "terraform-tests-vpc"
    alb_https_security_group_id     = "security-group-id"
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
      }

    ]

  }

  assert {
    condition = {
      for block in aws_security_group.environment_security_group.egress :
      block.description => toset(block.cidr_blocks)
      } == {
      "Egress rule 0" = toset(["172.65.64.208/30"])
      "Egress rule 1" = toset(["15.200.117.191/32", "172.65.64.208/30"])
    }
    error_message = "Egress cidr_blocks attributes are not as expected."
  }

  assert {
    condition = {
      for block in aws_security_group.environment_security_group.egress :
      block.description => block.protocol
      } == {
      "Egress rule 0" = "tcp"
      "Egress rule 1" = "udp"
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
    }
    error_message = "Egress to_port attributes are not as expected."
  }

  assert {
    condition     = length(aws_security_group.environment_security_group.egress) == 2
    error_message = "Egress does not exist."
  }

  assert {
    condition     = length(aws_vpc_security_group_ingress_rule.vpc_endpoints) == 1
    error_message = "expected aws_vpc_security_group_ingress_rule.vpc_endpoints to be created"
  }

  assert {
    condition     = aws_vpc_security_group_ingress_rule.vpc_endpoints[0].security_group_id == "vpce-security-group-id"
    error_message = "aws_vpc_security_group_ingress_rule security_group_id is not as expected"
  }
}




run "test_create_ecs_cluster_without_an_alb" {
  command = plan

  variables {
    application                     = "demodjango"
    environment                     = "dev"
    vpc_name                        = "terraform-tests-vpc"
    alb_https_security_group_id     = null
    vpc_endpoints_security_group_id = null
  }

  assert {
    condition     = length(aws_security_group.environment_security_group.ingress) == 1
    error_message = "Ingress includes more than containers in the same security group."
  }
}

