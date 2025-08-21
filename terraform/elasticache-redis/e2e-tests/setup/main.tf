terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6"
    }
  }
}

resource "aws_vpc" "main" {
  # checkov:skip=CKV2_AWS_11: As this VPC is used for E2E testing and torn down. No flow logging required 
  # checkov:skip=CKV2_AWS_12: As this VPC is used for E2E testing and torn down. Not required 
  cidr_block = "10.0.0.0/16"
  tags = {
    Name = "sandbox-elasticache-redis"
  }
}
resource "aws_subnet" "primary" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "eu-west-2a"
  tags = {
    Name = "sandbox-elasticache-redis-private-primary"
  }
}

resource "aws_security_group" "vpc-core-sg" {
  # checkov:skip=CKV2_AWS_5: False Positive in Checkov - https://github.com/bridgecrewio/checkov/issues/3010
  name        = "sandbox-elasticache-redis-base-sg"
  description = "Base security group for VPC"
  vpc_id      = aws_vpc.main.id
  tags = {
    Name = "sandbox-elasticache-redis-base-sg"
  }
}
