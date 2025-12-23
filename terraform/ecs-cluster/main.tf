data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

data "aws_ip_ranges" "service_ranges" {
  # {
  #    "3" = { services = [...], regions = [...] }
  #    "4" = { services = [...], regions = [...] }
  # }
  for_each = {
    for rule_num, rule in coalesce(var.egress_rules, []) :
    rule_num => rule.to.aws_cidr_blocks
    if try(rule.to.aws_cidr_blocks, null) != null
  }

  services = each.value.services
  regions  = each.value.regions
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
      description = "Egress rule ${egress.key}"
      from_port   = egress.value.from_port
      to_port     = egress.value.to_port
      protocol    = egress.value.protocol
      cidr_blocks = (
        egress.value.to.cidr_blocks != null
        ? tolist(egress.value.to.cidr_blocks)
        : (
          egress.value.to.aws_cidr_blocks != null
          ? data.aws_ip_ranges.service_ranges[egress.key].cidr_blocks
          : null
        )
      )
      security_groups = (
        egress.value.to.vpc_endpoints != null
        ? [var.vpc_endpoints_security_group_id]
        : null
      )
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

resource "aws_vpc_security_group_ingress_rule" "vpc_endpoints" {
  count                        = var.has_vpc_endpoints ? 1 : 0
  security_group_id            = var.vpc_endpoints_security_group_id
  ip_protocol                  = "tcp"
  from_port                    = 443
  to_port                      = 443
  referenced_security_group_id = aws_security_group.environment_security_group.id
}