output "certification_validation_records" {
  value = {
    for opt in aws_acm_certificate.acm.domain_validation_options : opt.domain_name => {
      name    = opt.resource_record_name
      type    = opt.resource_record_type
      records = [opt.resource_record_value]
    }
  }
  description = "Validation records for acm records"
}

output "endpoint_service_name" {
  value = aws_vpc_endpoint_service.private_service.service_name
}

output "vpce_azs" {
  value = aws_vpc_endpoint_service.private_service.availability_zones
}