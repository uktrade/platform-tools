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
  target = data.aws_security_group.https_security_group
  values = {
    id = "sg-00112233aabbccdef"
  }
}

run "test_create_ecs_cluster" {
  command = plan

  variables {
    application = "my_app"
    environment = "my_env"
    vpc_name    = "terraform-tests-vpc"
  }

  assert {
    condition     = aws_ecs_cluster.cluster.name == "my_app-my_env-cluster"
    error_message = "Cluster name should be: 'my_app-my_env-cluster'"
  }

  assert {
    condition     = aws_ecs_cluster.cluster.tags.application == "my_app"
    error_message = "application tag was not as expected"
  }

  assert {
    condition     = aws_ecs_cluster.cluster.tags.environment == "my_env"
    error_message = "environment tag was not as expected"
  }

  assert {
    condition     = aws_ecs_cluster.cluster.tags.managed-by == "DBT Platform - Environment Terraform"
    error_message = "managed-by tag was not as expected"
  }

  assert {
    condition     = aws_ecs_cluster_capacity_providers.capacity.cluster_name == "my_app-my_env-cluster"
    error_message = "Cluster name for capacity provider should be: 'my_app-my_env-cluster'"
  }

  assert {
    condition     = data.aws_security_group.https_security_group.name == "my_app-my_env-alb-https"
    error_message = "Security group name should be: 'my_app-my_env-alb-https'"
  }

  assert {
    condition     = aws_security_group.environment_security_group.tags.Name == "platform-my_app-my_env-env-sg"
    error_message = "Name tag was not as expected"
  }
}
