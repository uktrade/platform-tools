variables {
  zones     = ["a", "b", "c"]
  root-zone = "test-zone"
}

mock_provider "aws" {
}

run "aws_route53_zone_e2e_test" {
  command = apply

  assert {
    condition     = data.aws_route53_zone.root-zone.name == "test-zone"
    error_message = "Should be: test-zone"
  }

  assert {
    condition     = data.aws_route53_zone.root-zone.resource_record_set_count == 0
    error_message = "Should be: 0"
  }

}

run "aws_route53_record_e2e_test" {
  command = apply

  assert {
    condition     = [for el in aws_route53_record.ns-records : false if el.allow_overwrite == false][0] == false
    error_message = "Should be: false"
  }
}
