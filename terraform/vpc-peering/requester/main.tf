resource "aws_vpc_peering_connection" "this" {
  peer_owner_id = var.config.accepter_account_id
  peer_vpc_id   = var.config.accepter_vpc
  peer_region   = coalesce(var.config.accepter_region, "eu-west-2")
  vpc_id        = var.config.requester_vpc

  tags = local.tags
}

module "core" {
  source = "../core"

  vpc_id                    = var.config.requester_vpc
  subnet                    = var.config.accepter_subnet
  vpc_peering_connection_id = aws_vpc_peering_connection.this.id
  security_group_map        = coalesce(var.config.security_group_map, {})
  vpc_name                  = var.config.accepter_vpc_name
  source_vpc_id             = var.config.source_vpc_id
  target_hosted_zone_id     = var.config.target_hosted_zone_id
  accept_remote_dns         = var.config.accept_remote_dns
}
