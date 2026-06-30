mock_provider "aws" {
  mock_resource "aws_acm_certificate" {
    defaults = {
      domain_validation_options = [
        {
          domain_name           = "domain.uktrade"
          resource_record_name  = "_abc@domain.uktrade"
          resource_record_type  = "CNAME"
          resource_record_value = "_xyz.acm.validations.aws."
        }
      ]
    }
  }

  mock_resource "aws_lb" {
    defaults = {
      arn      = "arn:aws:elasticloadbalancing:eu-west-2:123456789012:loadbalancer/net/application-environment-nlb/abc"
      dns_name = "application-environment-nlb-abc.eu-west-2.amazonaws.com"
    }
  }

}

override_data {
  target = data.aws_vpc.vpc
  values = {
    id         = "vpc-00112233aabbccdef"
    cidr_block = "10.0.0.0/16"
    tags       = { "Name" : "vpc-22222222" }
  }
}

override_data {
  target = data.aws_subnets.private-subnets
  values = {
    ids = ["vpc-22222222-private-subnet-aaa111", "vpc-22222222-private-subnet-bbb222"]
  }
}

override_data {
  target = data.aws_security_group.env
  values = {
    name = "application-environment-environment"
  }
}

variables {
  name = "test-privatelink"
  config = {
    domain               = "domain.uktrade"
    producer_account_id  = "123456789012"
    producer_vpc_name    = "vpc-22222222"
    producer_application = "application"
    producer_environment = "environment"
    consumer_account_id  = "987654321098"
    consumer_cidr        = ["10.10.10.0/24"]
  }
}

run "setup_privatelink_producer" {
  command = apply


  assert {
    condition     = output.certification_validation_records["domain.uktrade"].name == "_abc@domain.uktrade"
    error_message = "Expected _abc@domain.uktrade"
  }

  assert {
    condition     = output.certification_validation_records["domain.uktrade"].type == "CNAME"
    error_message = "Expected CNAME"
  }

  assert {
    condition     = output.certification_validation_records["domain.uktrade"].records[0] == "_xyz.acm.validations.aws."
    error_message = "Expected _xyz.acm.validations.aws."
  }
}


run "invalid_cidr_blocks_fails" {
  command = plan

  variables {
    name = "test-cidr-input"
    config = {
      domain               = "domain.uktrade"
      producer_account_id  = "123456789012"
      producer_vpc_name    = "vpc-22222222"
      producer_application = "application"
      producer_environment = "environment"
      consumer_account_id  = "987654321098"
      consumer_cidr        = ["10.10.10.0/24", "not a cidr"]
    }
  }

  expect_failures = [var.config]
}

run "open_cidr_blocks_fails" {
  command = plan

  variables {
    name = "test-cidr-input"
    config = {
      domain               = "domain.uktrade"
      producer_account_id  = "123456789012"
      producer_vpc_name    = "vpc-22222222"
      producer_application = "application"
      producer_environment = "environment"
      consumer_account_id  = "987654321098"
      consumer_cidr        = ["0.0.0.0/0"]
    }
  }

  expect_failures = [var.config]
}
