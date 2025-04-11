
data "aws_lb" "environment_load_balancer" {
  name = "${var.application}-${var.environment}"
}

data "aws_lb_listener" "environment_alb_listener_https" {
  load_balancer_arn = data.aws_lb.environment_load_balancer.arn
  port              = 443
}

data "aws_lb_listener" "environment_alb_listener_http" {
  load_balancer_arn = data.aws_lb.environment_load_balancer.arn
  port              = 80
}

data "aws_security_group" "https_security_group" {
  name = "${var.application}-${var.environment}-alb-https"
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

resource "aws_lb_listener_rule" "https" {
  for_each = local.rules_with_priority

  listener_arn = data.aws_lb_listener.environment_alb_listener_https.arn
  priority     = each.value.priority

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.target_group[each.key].arn
  }

  condition {
    host_header {
      # TODO - The domain is different for prod environments
      values = each.value.host
    }
  }

  condition {
    path_pattern {
      values = each.value.path
    }
  }

  tags = local.tags
}


# Redirect all incoming HTTP traffic to the HTTPS listener
resource "aws_lb_listener_rule" "http_to_https" {
  listener_arn = data.aws_lb_listener.environment_alb_listener_http.arn
  priority     = 1

  action {
    type = "redirect"
    redirect {
      protocol    = "HTTPS"
      port        = "443"
      status_code = "HTTP_301"
    }
  }

  condition {
    path_pattern {
      values = ["/*"]
    }
  }

  tags = local.tags
}

resource "random_string" "tg_suffix" {
  for_each = local.web_services
  length  = 6
  min_lower = 6
  special = false
  lower = true
}

resource "aws_lb_target_group" "target_group" {
  for_each = local.web_services

  name = "${each.key}-tg-${random_string.tg_suffix[each.key].result}"
  port        = 443
  protocol    = "HTTPS"
  target_type = "ip"
  vpc_id      = data.aws_vpc.vpc.id
  deregistration_delay = 60
  tags = local.tags


  health_check {
    port                = lookup(each.value, "healthcheck_port", 8080)
    path                = lookup(each.value, "healthcheck_path", "/")
    protocol            = "HTTP"
    matcher             = lookup(each.value, "healthcheck_success_codes", "200")
    healthy_threshold   = lookup(each.value, "healthy_threshold", 3)
    unhealthy_threshold = lookup(each.value, "unhealthy_threshold", 3)
    interval            = tonumber(trim(lookup(each.value, "healthcheck_interval", "35s"), "s"))
    timeout             = tonumber(trim(lookup(each.value, "healthcheck_timeout", "30s"), "s"))
  }

}
