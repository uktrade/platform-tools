# VPC
resource "aws_vpc" "vpc" {
  # checkov:skip=CKV2_AWS_11: Requires wider discussion around log/event ingestion before implementing. To be picked up on conclusion of DBTP-974
  # checkov:skip=CKV2_AWS_12: Functionality provided via default_acl rather than default_security_group
  cidr_block           = "${var.arg_config.cidr}${local.vpc_cidr_mask}"
  enable_dns_hostnames = true
  tags = merge(
    local.tags,
    {
      Name = var.arg_name
    }
  )
}


# Subnets
##Private
resource "aws_subnet" "private" {
  for_each          = var.arg_config.az_map.private
  vpc_id            = aws_vpc.vpc.id
  cidr_block        = "${var.arg_config.cidr}.${each.value}${local.subnet_cidr_mask}"
  availability_zone = "${local.region}${each.key}"
  tags = merge(
    local.tags,
    {
      Name        = "${var.arg_name}-private-${local.region}${each.key}"
      subnet_type = "private"
    }
  )
}


##Public
resource "aws_subnet" "public" {
  for_each          = var.arg_config.az_map.public
  vpc_id            = aws_vpc.vpc.id
  cidr_block        = "${var.arg_config.cidr}.${each.value}${local.subnet_cidr_mask}"
  availability_zone = "${local.region}${each.key}"
  tags = merge(
    local.tags,
    {
      Name        = "${var.arg_name}-public-${local.region}${each.key}"
      subnet_type = "public"
    }
  )
}


## Public - Internet Gateway
resource "aws_internet_gateway" "public" {
  vpc_id = aws_vpc.vpc.id
  tags = merge(
    local.tags,
    {
      Name = "${var.arg_name}-ig-public"
    }
  )
}

# Public Routing
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.vpc.id
  tags = merge(
    local.tags,
    {
      Name = "${var.arg_name}-rt-public"
    }
  )
}

resource "aws_route" "public-route" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.public.id
}

resource "aws_route_table_association" "public" {
  for_each       = var.arg_config.az_map.public
  subnet_id      = aws_subnet.public[each.key].id
  route_table_id = aws_route_table.public.id
}


# NAT Gateway
resource "aws_eip" "public" {
  for_each = toset(var.arg_config.nat_gateways)
  domain   = "vpc"
  tags = merge(
    local.tags,
    {
      Name = "${var.arg_name}-nat-eip-${each.key}"
    }
  )
}

resource "aws_nat_gateway" "public" {
  for_each      = toset(var.arg_config.nat_gateways)
  allocation_id = aws_eip.public[each.key].id
  subnet_id     = aws_subnet.public[each.key].id
  tags = merge(
    local.tags,
    {
      Name = "${var.arg_name}-nat-gateway-${each.key}"
    }
  )
}

locals {
  nat_gateway_eips = [
    for key, nat in aws_eip.public : nat.public_ip
  ]
}

# SSM parameter with combined EIP values
resource "aws_ssm_parameter" "combined_nat_gateway_eips" {
  # checkov:skip=CKV_AWS_337:Ensure SSM parameters are using KMS CMK. Related ticket: https://uktrade.atlassian.net/browse/DBTP-946
  # checkov:skip=CKV2_AWS_34:AWS SSM Parameter should be Encrypted. Related ticket: https://uktrade.atlassian.net/browse/DBTP-946
  name  = "/${var.arg_name}/EGRESS_IPS"
  type  = "String"
  value = join(",", local.nat_gateway_eips)
  tags = merge(
    local.tags,
    {
      "copilot-application" = "__all__"
    }
  )

}


# Private Routing
resource "aws_route_table" "private" {
  for_each = toset(var.arg_config.nat_gateways)
  vpc_id   = aws_vpc.vpc.id
  tags = merge(
    local.tags,
    {
      Name = "${var.arg_name}-rt-private-${each.key}"
    }
  )
}

resource "aws_route" "private-route" {
  for_each               = toset(var.arg_config.nat_gateways)
  route_table_id         = aws_route_table.private[each.key].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.public[each.key].id
}

# If there is only 1 NAT gateway, only 1 route table is created and all subnets are assigned to this route table.
# If there are multiple NAT gateways, equivelent number of route tables are created and therfore matching AZ subnets are assigned to the matching route tables.
resource "aws_route_table_association" "private" {
  for_each       = var.arg_config.az_map.private
  subnet_id      = aws_subnet.private[each.key].id
  route_table_id = var.arg_config.nat_gateways == ["a"] ? aws_route_table.private["a"].id : aws_route_table.private[each.key].id
}


# Default ACL
resource "aws_default_network_acl" "default-acl" {
  default_network_acl_id = aws_vpc.vpc.default_network_acl_id
  ingress {
    protocol   = -1
    rule_no    = 100
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 0
    to_port    = 0
  }
  egress {
    protocol   = -1
    rule_no    = 100
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 0
    to_port    = 0
  }
  lifecycle {
    ignore_changes = [subnet_ids]
  }
  tags = merge(
    local.tags,
    {
      Name = "${var.arg_name}-base-sg"
    }
  )
}


# Base VPC security group
resource "aws_security_group" "vpc-core-sg" {
  name        = "${var.arg_name}-base-sg"
  description = "Base security group for VPC"
  vpc_id      = aws_vpc.vpc.id
  tags = merge(
    local.tags,
    {
      Name = "${var.arg_name}-base-sg"
    }
  )
}

resource "aws_security_group_rule" "vpc-core-ingress-all" {
  type                     = "ingress"
  description              = "Ingress from other containers in the same security group"
  from_port                = -1
  to_port                  = -1
  protocol                 = -1
  source_security_group_id = aws_security_group.vpc-core-sg.id
  security_group_id        = aws_security_group.vpc-core-sg.id
}

resource "aws_security_group_rule" "vpc-core-egress-all" {
  type              = "egress"
  description       = "Egress for all"
  from_port         = -1
  to_port           = -1
  protocol          = -1
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.vpc-core-sg.id
}


# VPC Enpoint required for RDS secrets manager
resource "aws_vpc_endpoint" "rds-vpc-endpoint" {
  vpc_id              = aws_vpc.vpc.id
  service_name        = "com.amazonaws.${local.region}.secretsmanager"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = data.aws_subnets.private-subnets.ids
  security_group_ids = [
    aws_security_group.rds-vpc-endpoint-sg.id,
    aws_security_group.vpc-core-sg.id
  ]
  tags = merge(
    local.tags,
    {
      Name = "${var.arg_name}-rds-endpoint"
    }
  )
}
# Security groups for RDS VPC endpoint
resource "aws_security_group" "rds-vpc-endpoint-sg" {
  name        = "${var.arg_name}-rds-endpoint-sg"
  description = "A security group to access the DB cluster"
  vpc_id      = aws_vpc.vpc.id
  tags = merge(
    local.tags,
    {
      Name = "${var.arg_name}-rds-endpoint-sg"
    }
  )
}

resource "aws_security_group_rule" "rds-db-ingress-fargate" {
  type                     = "ingress"
  description              = "Ingress from Fargate containers"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.vpc-core-sg.id
  security_group_id        = aws_security_group.rds-vpc-endpoint-sg.id
}

resource "aws_security_group_rule" "rds-db-ingress-lambda-to-db" {
  type                     = "ingress"
  description              = "Ingress from Lambda Functions to DB"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.rds-vpc-endpoint-sg.id
  security_group_id        = aws_security_group.rds-vpc-endpoint-sg.id
}

resource "aws_security_group_rule" "rds-db-ingress-lambda-to-sm" {
  type                     = "ingress"
  description              = "Ingress from Lambda Functions to Secrets Manager"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.rds-vpc-endpoint-sg.id
  security_group_id        = aws_security_group.rds-vpc-endpoint-sg.id
}

resource "aws_security_group_rule" "rds-db-egress-db-to-lambda" {
  type                     = "egress"
  description              = "Egress from DB to Lambda Functions"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.rds-vpc-endpoint-sg.id
  security_group_id        = aws_security_group.rds-vpc-endpoint-sg.id
}

resource "aws_security_group_rule" "rds-db-egress-sm-to-lambda" {
  type                     = "egress"
  description              = "Egress from Secrets Manager to Lambda Functions"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.rds-vpc-endpoint-sg.id
  security_group_id        = aws_security_group.rds-vpc-endpoint-sg.id
}

resource "aws_security_group_rule" "rds-db-egress-https" {
  type              = "egress"
  description       = "Egress for HTTPS"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.rds-vpc-endpoint-sg.id
}

data "aws_subnets" "private-subnets" {
  depends_on = [aws_subnet.private]
  filter {
    name   = "tag:Name"
    values = ["${var.arg_name}-private-*"]
  }
}

module "logs" {
  source      = "../logs"
  name_prefix = var.arg_name
}
