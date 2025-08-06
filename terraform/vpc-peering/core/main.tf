terraform {
  required_version = ">= 1.7.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6"
    }
  }
}

data "aws_route_tables" "peering-table" {
  vpc_id = var.vpc_id

  filter {
    name   = "tag:Name"
    values = ["*private*"]
  }
}

# If Prod there will be more than one route table, due to 1 x NAT per AZ.
resource "aws_route" "peering-route" {
  count                     = length(data.aws_route_tables.peering-table.ids)
  route_table_id            = tolist(data.aws_route_tables.peering-table.ids)[count.index]
  destination_cidr_block    = var.subnet
  vpc_peering_connection_id = var.vpc_peering_connection_id
}

resource "aws_security_group_rule" "peer-access" {
  for_each          = var.security_group_map
  type              = "ingress"
  from_port         = each.value
  to_port           = each.value
  protocol          = "tcp"
  cidr_blocks       = [var.subnet]
  security_group_id = each.key
  description       = "vpc peering from vpc: ${var.vpc_name}"
}

# Note: These next two resources are only run if you need to allow communication between ECS services.
# Also, vpc peering must be complete before these are run see docs
resource "aws_route53_vpc_association_authorization" "create-dns-association" {
  # If source_vpc is not defined as a VAR then this will NOT run.
  count   = can(var.source_vpc_id) && var.source_vpc_id != null && var.accept_remote_dns == null ? 1 : 0
  vpc_id  = var.source_vpc_id
  zone_id = var.target_hosted_zone_id
}

resource "aws_route53_zone_association" "authorize-dns-association" {
  # If bool accept_remote_dns is not defined or set to true then this will NOT run.
  count = can(var.accept_remote_dns) && var.accept_remote_dns != null ? 1 : 0

  vpc_id  = var.source_vpc_id
  zone_id = var.target_hosted_zone_id

  depends_on = [aws_route53_vpc_association_authorization.create-dns-association]
}
