data "aws_vpc" "vpc" {
  filter {
    name   = "tag:Name"
    values = [var.config.producer_vpc_name]
  }
}

data "aws_subnets" "private-subnets" {
  filter {
    name   = "tag:Name"
    values = ["${var.config.producer_vpc_name}-private-*"]
  }
}

data "aws_security_group" "env" {
  name = "${var.config.producer_application}-${var.config.producer_environment}-environment"
}

resource "aws_lb" "nlb" {
  name                             = "${var.config.producer_application}-${var.config.producer_environment}-nlb"
  load_balancer_type               = "network"
  internal                         = true
  subnets                          = tolist(data.aws_subnets.private-subnets.ids)
  enable_cross_zone_load_balancing = true
  enable_deletion_protection       = true

  security_groups = [aws_security_group.nlb.id]

  enforce_security_group_inbound_rules_on_private_link_traffic = "on"

  tags = local.tags
}

resource "aws_security_group" "nlb" {
  name        = "${var.config.producer_application}-${var.config.producer_environment}-nlb"
  vpc_id      = data.aws_vpc.vpc.id
  description = "NLB SG for ${var.config.producer_application} (PrivateLink)"

  tags = local.tags

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group_rule" "source-access" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = var.config.consumer_cidr
  security_group_id = aws_security_group.nlb.id
  description       = "PrivateLink Source CIDR to NLB for: ${var.config.producer_environment}"
}

resource "aws_security_group_rule" "nlb-to-ecs-egress" {
  type                     = "egress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = data.aws_security_group.env.id
  security_group_id        = aws_security_group.nlb.id
  description              = "NLB to ECS for: ${var.config.producer_environment}"
}

resource "aws_security_group_rule" "nlb-to-ecs-ingress" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.nlb.id
  security_group_id        = data.aws_security_group.env.id
  description              = "NLB to ECS for: ${var.config.producer_environment}"
}

resource "aws_security_group_rule" "healthcheck-env-egress" {
  type                     = "egress"
  from_port                = 8080
  to_port                  = 8080
  protocol                 = "tcp"
  source_security_group_id = data.aws_security_group.env.id
  security_group_id        = aws_security_group.nlb.id
  description              = "NLB to ECS healthcheck for: ${var.config.producer_environment}"
}

resource "aws_security_group_rule" "healthcheck-env-ingress" {
  type                     = "ingress"
  from_port                = 8080
  to_port                  = 8080
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.nlb.id
  security_group_id        = data.aws_security_group.env.id
  description              = "NLB to ECS healthcheck for: ${var.config.producer_environment}"
}


resource "aws_acm_certificate" "acm" {
  domain_name       = var.config.domain
  validation_method = "DNS"

  tags = local.tags

  lifecycle {
    create_before_destroy = true
  }
}


resource "aws_vpc_endpoint_service" "private_service" {
  network_load_balancer_arns = [aws_lb.nlb.arn]
  acceptance_required        = false

  tags = local.tags
}

resource "aws_vpc_endpoint_service_allowed_principal" "source_account" {
  vpc_endpoint_service_id = aws_vpc_endpoint_service.private_service.id
  principal_arn           = "arn:aws:iam::${var.config.consumer_account_id}:root"
}



