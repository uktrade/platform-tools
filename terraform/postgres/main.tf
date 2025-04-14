data "aws_vpc" "vpc" {
  filter {
    name   = "tag:Name"
    values = [var.vpc_name]
  }
}

data "aws_subnets" "private-subnets" {
  filter {
    name   = "tag:Name"
    values = ["${var.vpc_name}-private*"]
  }
}

resource "aws_security_group" "default" {
  name        = local.name
  vpc_id      = data.aws_vpc.vpc.id
  description = "Allow access from inside the VPC"

  ingress {
    description = "Local VPC access"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"

    cidr_blocks = [
      data.aws_vpc.vpc.cidr_block,
    ]
  }

  ingress {
    description = "Ingress from Lambda Functions to DB"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"

    self = true
  }

  ingress {
    description = "Ingress from Lambda Functions to Secrets Manager"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"

    self = true
  }

  egress {
    description = "Egress from DB to Lambda Functions"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"

    self = true
  }

  egress {
    description = "Egress from Secrets Manager to Lambda Functions"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"

    self = true
  }

  tags = local.tags
}
