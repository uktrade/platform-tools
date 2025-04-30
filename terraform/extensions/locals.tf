locals {
  plans = {
    opensearch = yamldecode(file("${path.module}/../opensearch/plans.yml"))
    postgres   = yamldecode(file("${path.module}/../postgres/plans.yml"))
    redis      = yamldecode(file("${path.module}/../elasticache-redis/plans.yml"))
  }

  # So we don't hit a Parameter Store limit, filter environment config for extensions so it only includes the defaults (`"*"`) and the current environment
  extensions_for_environment = {
    for extension_name, extension_config in var.args.extensions :
    extension_name => merge(extension_config, {
      environments = {
        for environment_name, environment_config in extension_config["environments"] :
        environment_name => environment_config if contains(["*", var.environment], environment_name)
      }
    })
  }

  // Select environment for each service and expand config from "*"
  extensions_with_default_and_environment_settings_merged = {
    for extension_name, extension_config in var.args.extensions :
    extension_name => merge(
      extension_config,
      merge(
        lookup(extension_config.environments, "*", {}),
        lookup(extension_config.environments, var.environment, {})
      )
    )
  }

  // If a plan is specified, expand it to the individual settings
  extensions_with_plan_expanded = {
    for extension_name, extension_config in local.extensions_with_default_and_environment_settings_merged :
    extension_name => merge(
      lookup(
        lookup(local.plans, extension_config.type, {}),
        lookup(extension_config, "plan", "NO-PLAN"),
        {}
      ),
      extension_config
    )
  }

  // Remove unnecessary fields
  extensions = {
    for extension_name, extension_config in local.extensions_with_plan_expanded :
    extension_name => {
      for k, v in extension_config : k => v if !contains(["environments", "plan"], k)
    }
  }

  // Filter extensions by type
  postgres = {
    for extension_name, extension_config in local.extensions :
    extension_name => extension_config if extension_config.type == "postgres"
  }
  s3 = {
    for extension_name, extension_config in local.extensions :
    extension_name => extension_config if extension_config.type == "s3"
  }
  redis = {
    for extension_name, extension_config in local.extensions :
    extension_name => extension_config if extension_config.type == "redis"
  }
  opensearch = {
    for extension_name, extension_config in local.extensions :
    extension_name => extension_config if extension_config.type == "opensearch"
  }
  monitoring = {
    for extension_name, extension_config in local.extensions :
    extension_name => extension_config if extension_config.type == "monitoring"
  }
  alb = {
    for extension_name, extension_config in local.extensions :
    extension_name => extension_config if extension_config.type == "alb"
  }
  cdn = {
    for extension_name, extension_config in local.extensions :
    extension_name => extension_config if extension_config.type == "alb"
  }
  datadog = {
    for extension_name, extension_config in local.extensions :
    extension_name => extension_config if extension_config.type == "datadog"
  }

  tags = {
    application         = var.args.application
    environment         = var.environment
    managed-by          = "DBT Platform - Terraform"
    copilot-application = var.args.application
    copilot-environment = var.environment
  }

  vpc_name            = var.args.env_config[var.environment]["vpc"]
  dns_account_id      = var.args.env_config[var.environment]["accounts"]["dns"]["id"]
  pipeline_account_id = var.args.env_config["*"]["accounts"]["deploy"]["id"]
}
