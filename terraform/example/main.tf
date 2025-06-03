locals {
  config       = yamldecode(file("${path.module}/platform-config.yml"))
  environments = local.config["environments"]
  env_config   = { for name, config in local.environments : name => merge(lookup(local.environments, "*", {}), config) }
  args = {
    application = "my-application"
    services    = local.config["extensions"]
    env_config  = local.env_config
  }
}

module "extensions-staging" {
  source      = "../extensions"
  args        = local.args
  environment = "my-environment"
}
