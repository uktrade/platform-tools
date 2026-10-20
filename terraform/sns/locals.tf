locals {
  allowed_account_ids = concat(
    [data.aws_caller_identity.current.account_id],
    var.config.allow_list
  )
}