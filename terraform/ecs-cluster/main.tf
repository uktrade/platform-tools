data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

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

  dynamic "ingress" {
    for_each = var.alb_https_security_group_id == null ? [] : [var.alb_https_security_group_id]
    content {
      description = "Allow from ALB"
      from_port   = 0
      to_port     = 0
      protocol    = "-1"
      security_groups = [
        ingress.value
      ]
    }
  }

  ingress {
    description = "Ingress from other containers in the same security group"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }

  dynamic "egress" {
    for_each = var.egress_rules == null ? [] : var.egress_rules
    content {
      description = "Allow traffic out"
      from_port   = var.egress_rules[egress.key].from_port
      to_port     = var.egress_rules[egress.key].to_port
      protocol    = var.egress_rules[egress.key].protocol
      cidr_blocks = var.egress_rules[egress.key].to.cidr_blocks
    }
  }


  dynamic "egress" {
    for_each = var.egress_rules == null ? [1] : []
    content {
      description = "Allow traffic out"
      protocol    = "-1"
      from_port   = 0
      to_port     = 0
      cidr_blocks = ["0.0.0.0/0"]
    }
  }
}
