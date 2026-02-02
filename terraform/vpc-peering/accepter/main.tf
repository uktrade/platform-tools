resource "aws_vpc_peering_connection_accepter" "this" {
  vpc_peering_connection_id = var.config.vpc_peering_connection_id
  auto_accept               = true

  tags = local.tags
}

module "core" {
  source = "../core"

  vpc_id                    = var.config.accepter_vpc
  subnet                    = var.config.requester_subnet
  vpc_peering_connection_id = aws_vpc_peering_connection_accepter.this.id
  security_group_map        = coalesce(var.config.security_group_map, {})
  vpc_name                  = var.config.requester_vpc_name
  source_vpc_id             = var.config.source_vpc_id
  target_hosted_zone_ids    = var.config.target_hosted_zone_ids
  accept_remote_dns         = var.config.accept_remote_dns
}
