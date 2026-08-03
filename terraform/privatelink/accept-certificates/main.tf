data "aws_ssm_parameters_by_path" "cert-domains" {
  path      = "/platform/privatelink/${var.application}/${var.environment}/certificate-domains"
  recursive = true
}


data "aws_acm_certificate" "acm" {
  for_each = nonsensitive(local.domain_map)

  domain   = each.key
  statuses = ["PENDING_VALIDATION", "ISSUED"]

  most_recent = true
}


resource "aws_acm_certificate_validation" "private-cert-validation" {
  for_each = nonsensitive(local.domain_map)

  certificate_arn = each.value.arn
}
