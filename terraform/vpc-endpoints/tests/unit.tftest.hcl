mock_provider "aws" {}

override_resource {
  target = aws_security_group.main
  values = {
    id = "sg-0123456789abcdef0"
  }
  override_during = plan
}

override_data {
  target = data.aws_vpc.vpc
  values = {
    id         = "vpc-00112233aabbccdef"
    cidr_block = "10.0.0.0/16"
  }
}

override_data {
  target = data.aws_subnets.private-subnets
  values = {
    ids = ["subnet-aaa111", "subnet-bbb222"]
  }
}

run "test_create_vpc_endpoints" {
  command = plan

  variables {
    application = "demodjango"
    environment = "dev"
    vpc_name    = "terraform-tests-vpc"
    instances = {
      ecr = {
        service_name = "com.amazonaws.eu-west-2.ecr.api"
      }
      s3 = {
        service_name = "com.amazonaws.eu-west-2.s3"
      }
    }
  }

  assert {
    condition     = aws_vpc_endpoint.main["ecr"].tags.application == "demodjango"
    error_message = "application tag was not as expected"
  }

  assert {
    condition     = aws_vpc_endpoint.main["ecr"].tags.environment == "dev"
    error_message = "environment tag was not as expected"
  }

  assert {
    condition     = aws_vpc_endpoint.main["ecr"].tags.managed-by == "DBT Platform - Environment Terraform"
    error_message = "managed-by tag was not as expected"
  }

  assert {
    condition     = aws_vpc_endpoint.main["ecr"].tags.Name == "demodjango-dev-ecr"
    error_message = "Name tag was not as expected"
  }

  assert {
    condition     = aws_vpc_endpoint.main["ecr"].security_group_ids == toset([aws_security_group.main.id])
    error_message = "aws_vpc_endpoint security_group_ids are not as expected"
  }

  assert {
    condition     = aws_vpc_endpoint.main["ecr"].service_name == "com.amazonaws.eu-west-2.ecr.api"
    error_message = "aws_vpc_endpoint service_name is not as expected"
  }

  assert {
    condition     = aws_vpc_endpoint.main["s3"].service_name == "com.amazonaws.eu-west-2.s3"
    error_message = "aws_vpc_endpoint service_name is not as expected"
  }

  assert {
    condition     = aws_vpc_endpoint.main["ecr"].vpc_endpoint_type == "Interface"
    error_message = "aws_vpc_endpoint vpc_endpoint_type is not as expected"
  }

  assert {
    condition     = aws_vpc_endpoint.main["s3"].vpc_endpoint_type == "Interface"
    error_message = "aws_vpc_endpoint vpc_endpoint_type is not as expected"
  }

  assert {
    condition     = aws_vpc_endpoint.main["ecr"].vpc_id == "vpc-00112233aabbccdef"
    error_message = "aws_vpc_endpoint vpc_id is not as expected"
  }

  assert {
    condition     = aws_vpc_endpoint.main["s3"].vpc_id == "vpc-00112233aabbccdef"
    error_message = "aws_vpc_endpoint vpc_id is not as expected"
  }

  assert {
    condition     = toset(aws_vpc_endpoint.main["ecr"].subnet_ids) == toset(["subnet-aaa111", "subnet-bbb222"])
    error_message = "aws_vpc_endpoint subnet_ids are not as expected"
  }

  assert {
    condition     = toset(aws_vpc_endpoint.main["s3"].subnet_ids) == toset(["subnet-aaa111", "subnet-bbb222"])
    error_message = "aws_vpc_endpoint subnet_ids are not as expected"
  }

  assert {
    condition     = length(aws_vpc_endpoint.main["ecr"].security_group_ids) == 1
    error_message = "aws_vpc_endpoint security_group_ids are not as expected"
  }

  assert {
    condition     = length(aws_vpc_endpoint.main["s3"].security_group_ids) == 1
    error_message = "aws_vpc_endpoint security_group_ids are not as expected"
  }

  assert {
    condition     = aws_security_group.main.name == "demodjango-dev-vpc-endpoints"
    error_message = "security group name should be \"demodjango-dev-vpc-endpoints\""
  }

  assert {
    condition     = output.security_group_id == aws_security_group.main.id
    error_message = "aws_security_group id is not as expected"
  }

  assert {
    condition     = aws_security_group.main.vpc_id == "vpc-00112233aabbccdef"
    error_message = "aws_security_group vpc_id is not as expected"
  }

  assert {
    condition     = aws_security_group.main.tags.application == "demodjango"
    error_message = "aws_security_group application tag was not as expected"
  }

  assert {
    condition     = aws_security_group.main.tags.environment == "dev"
    error_message = "aws_security_group environment tag was not as expected"
  }

  assert {
    condition     = aws_security_group.main.tags.managed-by == "DBT Platform - Environment Terraform"
    error_message = "aws_security_group managed-by tag was not as expected"
  }

  assert {
    condition     = aws_security_group.main.tags.Name == "platform-demodjango-dev-vpce-sg"
    error_message = "aws_security_group Name tag was not as expected"
  }
}
