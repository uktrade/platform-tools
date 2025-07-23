data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

data "aws_lb" "environment_load_balancer" {
  name = "${var.application}-${var.environment}"
}

data "aws_lb_listener" "environment_alb_listener_http" {
  load_balancer_arn = data.aws_lb.environment_load_balancer.arn
  port              = 80
}

resource "aws_ecs_cluster" "cluster" {
  name = local.cluster_name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = local.tags
}

resource "aws_ecs_cluster_capacity_providers" "capacity" {
  cluster_name = aws_ecs_cluster.cluster.name

  capacity_providers = ["FARGATE", "FARGATE_SPOT"]
}

resource "aws_service_discovery_private_dns_namespace" "private_dns_namespace" {
  name        = "${var.environment}.${var.application}.services.local"
  description = "Private DNS namespace for services"
  vpc         = data.aws_vpc.vpc.id
  tags        = local.tags
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
  # checkov:skip=CKV_AWS_382: Required for general internet access
  # checkov:skip=CKV2_AWS_5: TODO - This will be used by service Terraform in the future
  name        = "${var.application}-${var.environment}-environment"
  description = "Managed by Terraform"
  vpc_id      = data.aws_vpc.vpc.id
  tags        = local.sg_env_tags

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
