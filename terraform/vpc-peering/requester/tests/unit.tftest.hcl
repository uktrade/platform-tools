mock_provider "aws" {}

variables {
  config = {
    id                  = "pcx-12345678"
    accepter_account_id = "123456789"
    accepter_subnet     = "10.10.10.0/24"
    accepter_vpc        = "vpc-22222222"
    accepter_vpc_name   = "vpc-accepter"
    requester_vpc       = "vpc-11111111"
  }
}

run "request_connection" {
  command = plan

  assert {
    # Ensure the VPC peering connection exists with the request
    condition     = aws_vpc_peering_connection.this.peer_vpc_id == "vpc-22222222"
    error_message = "VPC peering connection was not created."
  }
}
