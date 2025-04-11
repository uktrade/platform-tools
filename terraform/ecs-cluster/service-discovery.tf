data "aws_vpc" "vpc" {
  filter {
    name   = "tag:Name"
    values = [var.vpc_name]
  }
}

resource "aws_service_discovery_private_dns_namespace" "private_dns_namespace" {
  name        = "${var.environment}.${var.application}.local-tf"
  description = "demoddjango private dns namespace"
  vpc         = data.aws_vpc.vpc.id
}

resource "aws_service_discovery_service" "service_discovery_service" {
  for_each = local.web_services
  name     = each.key

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.private_dns_namespace.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    dns_records {
      ttl  = 10
      type = "SRV"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}
