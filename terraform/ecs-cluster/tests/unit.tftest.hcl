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
    application                 = "demodjango"
    environment                 = "dev"
    vpc_name                    = "terraform-tests-vpc"
    alb_https_security_group_id = "security-group-id"
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
}
