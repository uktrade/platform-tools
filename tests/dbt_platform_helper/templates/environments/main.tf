# {% extra_header %}
# {% version_info %}
locals {
  config = yamldecode(file("../../../platform-config.yml"))
  environments = local.config["environments"]
  env_config   = { for name, config in local.environments : name => merge(lookup(local.environments, "*", {}), config) }
  args = {
    application    = "{{ application }}"
    services       = local.config["extensions"]
    dns_account_id = local.env_config["{{ environment }}"]["accounts"]["dns"]["id"]
  }
}

terraform {
  required_version = "~> 1.8"
  backend "s3" {
    bucket         = "terraform-platform-state-{{ config.accounts.deploy.name }}"
    key            = "tfstate/application/{{ application }}-{{ environment }}.tfstate"
    region         = "eu-west-2"
    encrypt        = true
    kms_key_id     = "alias/terraform-platform-state-s3-key-{{ config.accounts.deploy.name }}"
    dynamodb_table = "terraform-platform-lockdb-{{ config.accounts.deploy.name }}"
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5"
    }
  }
}

module "extensions" {
  source = "git::https://github.com/uktrade/terraform-platform-modules.git//extensions?depth=1&ref={{terraform_platform_modules_version}}"

  args        = local.args
  environment = "{{ environment }}"
  vpc_name    = "{{ config.vpc }}"
}

/* 
Clean up because terraform modules were initially deployed with a -tf suffix.  This block moves those modules to naming without a suffix.
Can be removed once all services have moved to the new naming.
*/
moved {
  from = module.extensions-tf
  to   = module.extensions
}
