locals {
  allowed_account_ids = concat(
    [data.aws_caller_identity.current.account_id],
    var.config.allowed_account_ids
  )

  target_ou_id = data.aws_organizations_organizational_units.ou.children[0].id
  root_id      = data.aws_organizations_organization.org.roots[0].id
  org_id       = data.aws_organizations_organization.org.id
}