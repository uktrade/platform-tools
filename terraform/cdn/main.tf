data "aws_secretsmanager_secret_version" "origin_verify_secret_version" {
  for_each  = toset(length(local.cdn_domains_list) > 0 ? [""] : [])
  secret_id = var.origin_verify_secret_id
}
