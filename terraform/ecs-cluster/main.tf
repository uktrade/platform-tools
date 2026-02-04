data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

data "aws_ip_ranges" "service_ranges" {
  # {
  #    "myrule" = { services = [...], regions = [...] }
  #    "myotherrule" = { services = [...], regions = [...] }
  # }
  for_each = {
    for rule_name, rule in coalesce(var.egress_rules, {}) :
    rule_name => rule.destination.aws_cidr_blocks
    if rule.destination.aws_cidr_blocks != null
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
  # checkov:skip=CKV2_AWS_5: Not applicable
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
    for_each = coalesce(var.egress_rules, {})
    content {
      description = "Egress: ${egress.key}"
      from_port   = egress.value.from_port
      to_port     = egress.value.to_port
      protocol = (
        egress.value.protocol == "all"
        ? "-1"
        : egress.value.protocol
      )
      cidr_blocks = (
        egress.value.destination.cidr_blocks != null
        ? egress.value.destination.cidr_blocks
        : (
          egress.value.destination.aws_cidr_blocks != null
          ? data.aws_ip_ranges.service_ranges[egress.key].cidr_blocks
          : null
        )
      )
      security_groups = (
        egress.value.destination.vpc_endpoints != null
        ? [var.vpc_endpoints_security_group_id]
        : null
      )
    }
  }

  # If egress_rules is omitted, permit all egress (for backwards compatibility).
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

data "aws_ssm_parameters_by_path" "vpc_peering" {
  path      = "/platform/vpc-peering/"
  recursive = true
}

resource "aws_vpc_security_group_ingress_rule" "vpc_peering" {
  for_each          = nonsensitive(local.vpc_peering_for_this_sg)
  security_group_id = aws_security_group.environment_security_group.id
  ip_protocol       = "tcp"
  from_port         = each.value["port"]
  to_port           = each.value["port"]
  cidr_ipv4         = each.value["source-vpc-cidr"]
  description       = "VPC peering traffic from VPC '${each.value["source-vpc-name"]}'"
}

