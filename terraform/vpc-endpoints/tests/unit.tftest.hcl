mock_provider "aws" {}

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
    condition     = aws_security_group.main.vpc_id == "vpc-00112233aabbccdef"
    error_message = "aws_security_group vpc_id is not as expected"
  }

  # TODO: tags
  # TODO: assigned IP address should be a module output
}