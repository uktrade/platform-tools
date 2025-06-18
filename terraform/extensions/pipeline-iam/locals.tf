locals {
  dns_account_id      = var.env_config[var.environment]["accounts"]["dns"]["id"]
  pipeline_account_id = var.env_config["*"]["accounts"]["deploy"]["id"]
  deploy_account_name = var.env_config[var.environment]["accounts"]["deploy"]["name"]

  account_region = "${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}"
}
