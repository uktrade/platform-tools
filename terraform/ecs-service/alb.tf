
data "aws_lb" "environment_load_balancer" {
  name = "${var.application}-${var.environment}"
}

data "aws_lb_listener" "environment_alb_listener_https" {
  load_balancer_arn = data.aws_lb.environment_load_balancer.arn
  port              = 443
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

resource "random_string" "tg_suffix" {
  length    = 6
  min_lower = 6
  special   = false
  lower     = true
}

resource "aws_lb_target_group" "target_group" {

  name                 = "${local.service_name}-tg-${random_string.tg_suffix.result}"
  port                 = 443
  protocol             = "HTTPS"
  target_type          = "ip"
  vpc_id               = data.aws_vpc.vpc.id
  deregistration_delay = 60
  tags                 = local.tags


  health_check {
    port                = coalesce(var.service_config.http.healthcheck.port, 8080)
    path                = coalesce(var.service_config.http.healthcheck.path, "/")
    protocol            = "HTTP"
    matcher             = coalesce(var.service_config.http.healthcheck.success_codes, "200")
    healthy_threshold   = coalesce(var.service_config.http.healthcheck.healthy_threshold, 3)
    unhealthy_threshold = coalesce(var.service_config.http.healthcheck.unhealthy_threshold, 3)
    interval            = tonumber(trim(coalesce(var.service_config.http.healthcheck.interval, "35s"), "s"))
    timeout             = tonumber(trim(coalesce(var.service_config.http.healthcheck.timeout, "30s"), "s"))
  }
}
