locals {
  tags = {
    managed-by  = "DBT Platform - Terraform"
    application = var.application
    environment = var.environment
  }

  raw_domain_list = flatten([
    for val in data.data.aws_ssm_parameters_by_path.cert-domains.values : [
      for domain, attributes in jsondecode(val) : {
        domain     = domain
        attributes = attributes
      }
    ]
  ])
  domain_map = {
    for item in local.raw_domain_list : item.domain => item.attributes
  }
}
