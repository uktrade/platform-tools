locals {
  allowed_account_ids = concat(
    [data.aws_caller_identity.current.account_id],
    var.config.allowed_account_ids
  )

  org_ids = {
    prod = [
      "o-hzyhz93zuk/r-*/ou-vjka-u5ykvrkw/*", # production
      "o-hzyhz93zuk/r-*/ou-vjka-lgjua3ci/*"  # dbt platform production
    ]
    non_prod = [
      "o-hzyhz93zuk/r-*/ou-vjka-gs0pbvkj/*", # non-prod
      "o-hzyhz93zuk/r-*/ou-vjka-pdqz7890/*", # dbt patform non-prod
      "o-hzyhz93zuk/r-*/ou-vjka-usz556y0/*"  # sandbox
    ]
  }

  tags = {
    application = var.application
    environment = var.environment
    managed-by  = "DBT Platform - Terraform"
  }
}