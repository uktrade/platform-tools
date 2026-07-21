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
  # checkov:skip=CKV_AWS_91: work with SRE to set up logging for NLBs
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

resource "aws_security_group_rule" "nlb-allow-inbound-from-consumer" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = var.config.consumer_cidr
  security_group_id = aws_security_group.nlb.id
  description       = "PrivateLink Source CIDR to NLB for: ${var.config.producer_environment}"
}

resource "aws_security_group_rule" "nlb-allow-outbound-to-ecs" {
  type                     = "egress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = data.aws_security_group.env.id
  security_group_id        = aws_security_group.nlb.id
  description              = "NLB to ECS for: ${var.config.producer_environment}"
}

resource "aws_security_group_rule" "nlb-allow-healthcheck-outbound-to-ecs" {
  type                     = "egress"
  from_port                = var.healthcheck-port
  to_port                  = var.healthcheck-port
  protocol                 = "tcp"
  source_security_group_id = data.aws_security_group.env.id
  security_group_id        = aws_security_group.nlb.id
  description              = "NLB to ECS healthcheck for: ${var.config.producer_environment}"
}


resource "aws_ssm_parameter" "security_group_rules" {
  # checkov:skip=CKV2_AWS_34: does not contain secret values
  for_each = {
    "ecs-allow-inbound-from-nlb" : {
      "port"           = 443
      "application"    = var.config.producer_application
      "environment"    = var.config.producer_environment
      "security-group" = data.aws_security_group.env.id
      "protocol"       = "tcp"
      "description"    = "NLB to ECS for: ${var.config.producer_environment}"
      "source-sg"      = aws_security_group.nlb.id
    },
    "ecs-allow-healthcheck-inbound-from-nlb" : {
      "port"           = var.healthcheck-port
      "application"    = var.config.producer_application
      "environment"    = var.config.producer_environment
      "security-group" = data.aws_security_group.env.id
      "protocol"       = "tcp"
      "description"    = "NLB to ECS healthcheck for: ${var.config.producer_environment}"
      "source-sg"      = aws_security_group.nlb.id
    },

  }
  name = "/platform/privatelink/${each.value.application}/${each.value.environment}/env-security-groups/rules/${each.key}"
  type = "String"
  value = jsonencode({
    "security-group-id" = each.value.security-group
    "source-sg"         = each.value.source-sg
    "port"              = each.value.port
    "application"       = each.value.application
    "environment"       = each.value.environment
    "protocol"          = each.value.protocol
    "description"       = each.value.description
  })
  description = "An SSM parameter used by the environment Terraform to determine whether to add an ingress security group rule to the environment service SG."
}

resource "aws_acm_certificate" "acm" {
  domain_name       = var.config.domain
  validation_method = "DNS"

  tags = local.tags

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_ssm_parameter" "cert_domain" {
  # checkov:skip=CKV2_AWS_34: does not contain secret values
  name = "/platform/privatelink/${var.config.producer_application}/${var.config.producer_environment}/certificate-domains/${var.config.domain}"
  type = "String"
  value = jsonencode({
    for opt in aws_acm_certificate.acm.domain_validation_options : opt.domain_name => {
      name    = opt.resource_record_name
      type    = opt.resource_record_type
      records = [opt.resource_record_value]
    }
  })
  description = "An SSM parameter used by the environment Terraform to activate pending domains."
}


resource "aws_vpc_endpoint_service" "private_service" {
  # checkov:skip=CKV_AWS_123: manual acceptance is done via SRE approving and applying terraform
  network_load_balancer_arns = [aws_lb.nlb.arn]
  acceptance_required        = false

  tags = local.tags
}

resource "aws_vpc_endpoint_service_allowed_principal" "source_account" {
  vpc_endpoint_service_id = aws_vpc_endpoint_service.private_service.id
  principal_arn           = "arn:aws:iam::${var.config.consumer_account_id}:root"
}



