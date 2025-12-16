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
  service_name      = var.instances.ecr.service_name
  vpc_endpoint_type = "Interface"
  vpc_id            = data.aws_vpc.vpc.id
  subnet_ids        = data.aws_subnets.private-subnets.ids
}