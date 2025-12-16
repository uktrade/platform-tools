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
    vpc_name = "terraform-tests-vpc"
    instances = {
      ecr = {
        service_name = "com.amazonaws.eu-west-2.ecr.api"
      }
    }
  }

  assert {
    condition     = aws_vpc_endpoint.main.service_name == "com.amazonaws.eu-west-2.ecr.api"
    error_message = "aws_vpc_endpoint service_name is not as expected"
  }

  assert {
    condition     = aws_vpc_endpoint.main.vpc_endpoint_type == "Interface"
    error_message = "aws_vpc_endpoint vpc_endpoint_type is not as expected"
  }

  assert {
    condition     = aws_vpc_endpoint.main.vpc_id == "vpc-00112233aabbccdef"
    error_message = "aws_vpc_endpoint vpc_id is not as expected"
  }

  assert {
    condition     = toset(aws_vpc_endpoint.main.subnet_ids) == toset(["subnet-aaa111", "subnet-bbb222"])
    error_message = "aws_vpc_endpoint subnet_ids are not as expected"
  }

  # TODO: more than one vpc endpoint
  # TODO: security_group_ids
  # TODO: assigned IP address should be a module output
}