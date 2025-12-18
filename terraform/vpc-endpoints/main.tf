data "aws_vpc" "vpc" {
  filter {
    name   = "tag:Name"
    values = [var.vpc_name]
  }
}

data "aws_subnets" "private-subnets" {
  filter {
    name   = "tag:Name"
    values = ["${var.vpc_name}-private-*"]
  }
}

resource "aws_vpc_endpoint" "main" {
  for_each           = var.instances
  service_name       = each.value.service_name
  vpc_endpoint_type  = "Interface"
  vpc_id             = data.aws_vpc.vpc.id
  subnet_ids         = data.aws_subnets.private-subnets.ids
  security_group_ids = [aws_security_group.main.id]
  tags               = local.tags
}

resource "aws_security_group" "main" {
  name   = "${var.application}-${var.environment}-vpc-endpoints"
  vpc_id = data.aws_vpc.vpc.id
  tags   = local.tags
  # Rules are to be declared using aws_vpc_security_group_ingress_rule
  # and aws_vpc_security_group_egress_rule resources.
}
