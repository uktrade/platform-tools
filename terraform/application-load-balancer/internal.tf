data "aws_security_group" "vpc_origins" {
  vpc_id = data.aws_vpc.vpc.id
  name   = "CloudFront-VPCOrigins-Service-SG"
}

resource "aws_lb" "internal" {
  name               = "${var.application}-${var.environment}-internal"
  load_balancer_type = "application"
  internal           = true
  subnets            = data.aws_subnets.private-subnets.ids
  security_groups    = [aws_security_group.internal_alb.id]
  access_logs {
    bucket  = var.environment == "prod" ? "alb-access-logs-prod-812359060647-eu-west-2-an" : "alb-access-logs-non-prod-812359060647-eu-west-2-an"
    prefix  = "${var.application}/${var.environment}"
    enabled = true
  }

  tags = local.tags

  drop_invalid_header_fields = true
  enable_deletion_protection = false # TODO: change to true once migration to internal ALBs is complete
}

# HTTPS listener only (not HTTP)
resource "aws_lb_listener" "internal" {
  depends_on = [aws_acm_certificate_validation.cert_validate]

  load_balancer_arn = aws_lb.internal.arn
  port              = local.protocols.https.port
  protocol          = "HTTPS"
  ssl_policy        = local.protocols.https.ssl_policy
  certificate_arn   = local.protocols.https.certificate_arn
  tags              = local.tags
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.default.arn
  }
}

resource "aws_security_group" "internal_alb" {
  name        = "${var.application}-${var.environment}-internal-alb"
  description = "Managed by Terraform"
  vpc_id      = data.aws_vpc.vpc.id
  tags        = local.tags
  ingress {
    description     = "Allow from CloudFront on port ${local.protocols.https.port}"
    from_port       = local.protocols.https.port
    to_port         = local.protocols.https.port
    protocol        = "tcp"
    security_groups = [data.aws_security_group.vpc_origins.id]
  }
  egress {
    description = "Allow traffic out"
    protocol    = "tcp"
    from_port   = 0
    to_port     = 65535
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_lb_target_group" "default" {
  name        = "${var.application}-${var.environment}-default"
  port        = 80
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = data.aws_vpc.vpc.id
  tags        = local.tags
}

resource "aws_cloudfront_vpc_origin" "internal" {
  vpc_origin_endpoint_config {
    name                   = "${var.application}-${var.environment}"
    arn                    = aws_lb.internal.arn
    http_port              = local.protocols.http.port
    https_port             = local.protocols.https.port
    origin_protocol_policy = "https-only"
    origin_ssl_protocols {
      items    = ["TLSv1.2"]
      quantity = 1
    }
  }
  tags = local.tags
}

resource "aws_ram_resource_share" "vpc_origin" {
  provider                  = aws.us_east_1
  name                      = "${var.application}-${var.environment}-vpc-origin"
  allow_external_principals = true
  tags                      = local.tags
}

resource "aws_ram_resource_association" "vpc_origin" {
  provider           = aws.us_east_1
  resource_arn       = aws_cloudfront_vpc_origin.internal.arn
  resource_share_arn = aws_ram_resource_share.vpc_origin.arn
}

resource "aws_ram_principal_association" "vpc_origin" {
  provider           = aws.us_east_1
  principal          = var.dns_account_id
  resource_share_arn = aws_ram_resource_share.vpc_origin.arn
}
