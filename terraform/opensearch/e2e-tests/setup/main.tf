terraform {
  required_version = "~> 1.7"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5"
    }
  }
}

resource "aws_vpc" "main" {
  # checkov:skip=CKV2_AWS_11: As this VPC is used for E2E testing and torn down. No flow logging required
  # checkov:skip=CKV2_AWS_12: As this VPC is used for E2E testing and torn down. Not required 
  cidr_block = "10.0.0.0/16"
  tags = {
    Name = "sandbox-opensearch"
  }
}
resource "aws_subnet" "primary" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "eu-west-2a"
  tags = {
    Name = "sandbox-opensearch-private-primary"
  }
}
