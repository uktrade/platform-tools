locals {
  authorise_route53_vpc_association = can(var.source_vpc_id) && var.source_vpc_id != null && var.accept_remote_dns == null
  accept_route53_zone_association   = can(var.accept_remote_dns) && var.accept_remote_dns != null
}

