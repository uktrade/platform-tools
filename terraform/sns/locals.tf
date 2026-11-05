locals {
  allowed_account_ids = concat(
    [data.aws_caller_identity.current.account_id],
    var.config.allowed_account_ids
  )

  org_ids = {
    prod = ["o-hzyhz93zuk/r-*/ou-vjka-gs0pbvkj/*"]
    non_prod = [
      "o-hzyhz93zuk/r-*/ou-vjka-u5ykvrkw/*", # non-prod
      "o-hzyhz93zuk/r-*/ou-vjka-usz556y0/*"  # sandbox
    ]
  }
}