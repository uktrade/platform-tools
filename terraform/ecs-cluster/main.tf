data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "aws_ecs_cluster" "cluster" {
  name = local.cluster_name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  configuration {
    execute_command_configuration {
      logging = "DEFAULT"
    }
  }

  tags = local.tags
}

resource "aws_ecs_cluster_capacity_providers" "capacity" {
  cluster_name = aws_ecs_cluster.cluster.name

  capacity_providers = ["FARGATE", "FARGATE_SPOT"]
}

data "aws_security_group" "https_security_group" {
  name = "${var.application}-${var.environment}-alb-https"
}

data "aws_vpc" "vpc" {
  filter {
    name   = "tag:Name"
    values = [var.vpc_name]
  }
}

resource "aws_security_group" "environment_security_group" {
  name        = "${var.application}-${var.environment}-environment"
  description = "Managed by Terraform"
  vpc_id      = data.aws_vpc.vpc.id
  tags        = local.tags

  ingress {
    description = "Allow from ALB"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    security_groups = [
      data.aws_security_group.https_security_group.id
    ]
  }

  ingress {
    description = "Ingress from other containers in the same security group"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }

  egress {
    description = "Allow traffic out"
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }
}
