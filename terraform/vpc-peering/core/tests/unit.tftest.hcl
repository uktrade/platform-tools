mock_provider "aws" {}

variables {
  vpc_peering_connection_id = "123456"
  accept_remote_dns         = null
  target_hosted_zone_id     = "Z12345"
  source_vpc_id             = "vpc-12345"
  security_group_map        = {}
  vpc_name                  = "my-vpc"
  subnet                    = "10.10.10.0/24"
  vpc_id                    = "vpc-12345"
}

override_data {
  target = data.aws_route_tables.peering-table
  values = {
    vpc_id = "vpc-12345"
    ids    = ["rtb-12345", "rtb-54321"]
  }
}

run "check_connection" {
  command = plan

  assert {
    # Check for valid subnet to ensure the connection can be made.
    condition     = aws_route.peering-route[0].destination_cidr_block == "10.10.10.0/24"
    error_message = "Incorrect destination subnet"
  }
}

run "is_source_vpc_service_to_service" {
  command = plan

  assert {
    # Check if able to create DNS association if a source_vpc is set as a VAR.
    condition     = aws_route53_vpc_association_authorization.create-dns-association[0].vpc_id == "vpc-12345"
    error_message = "Incorrect vpc id"
  }
}

run "is_accept_dns_service_to_service" {
  command = plan

  variables {
    accept_remote_dns = true
  }

  assert {
    # Check to see if association is authorized if accept_remote_dns is true
    condition     = aws_route53_zone_association.authorize-dns-association[0].zone_id == "Z12345"
    error_message = "Incorrect zone id"
  }
}
