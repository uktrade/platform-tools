locals {
  tags = {
    application = var.application
    environment = var.environment
    managed-by  = "DBT Platform - Terraform"
  }

  region_account = "${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}"
  cluster_name   = "${var.application}-${var.environment}-tf"

  is_production_env = contains(["prod", "production", "PROD", "PRODUCTION"], var.environment)
  log_destination_arn = local.is_production_env ? "arn:aws:logs:eu-west-2:812359060647:destination:cwl_log_destination" : "arn:aws:logs:eu-west-2:812359060647:destination:platform-logging-logstash-distributor-non-production"

  bucket_access_services = toset(flatten([ for bucket_key, bucket_config in var.s3_config :
    [for service in bucket_config.services : service if contains(keys(var.services), service)]
  ]))

  # Merge environment-specific and default ("*") config for each service
  # This makes fields like `path_patterns` available across different environments without unnecessary repetition
  services_with_default_and_environment_settings_merged = {
    for service_name, service_config in var.services :
    service_name => merge(
      {
        type = service_config.type
      },
      merge(
        lookup(service_config.environments, "*", {}),
        lookup(service_config.environments, var.environment, {})
      )
    )
  }

  # Filter only web services out of all merged services
  web_services = {
    for service_name, service_config in local.services_with_default_and_environment_settings_merged :
    service_name => service_config
    if service_config.type == "web-service"
  }

  # Build a config object for each web service to define ALB listener rules
  listener_rules_config = {
    for service_name, service_config in local.web_services :
    service_name => {
      service = service_name
      host    = lookup(service_config, "hostnames", ["${service_name}.${var.environment}.${var.application}.uktrade.digital"])
      path    = lookup(service_config, "path_patterns", ["/*"])
      # If specified in platform-config, gives the option to override the auto-assigned rule priority
      rule_priority  = lookup(service_config, "web_service_priority", null)
      # Determine whether the rule is a catch-all root ("/" or "/*")
      is_root_path = alltrue([for path in lookup(service_config, "path_patterns", ["/*"]) : (path == "/" || path == "/*")])
    }
  }

  # Group rules with root paths ("/" or "/*") into a sorted list
  root_rules_list = [
    for service_name in sort(keys(local.listener_rules_config)) :
    local.listener_rules_config[service_name]
    if local.listener_rules_config[service_name].is_root_path == true
  ]

  # Group rules with non-root paths (e.g. "/api", "/web") into a sorted list
  non_root_rules_list = [
    for service_name in sort(keys(local.listener_rules_config)) :
    local.listener_rules_config[service_name]
    if local.listener_rules_config[service_name].is_root_path == false
  ]

  # Place non-root rules first (more specific), followed by root rules (catch-all)
  combined_rules_list = concat(local.non_root_rules_list, local.root_rules_list)

  # Assign listener rule priorities:
  # - Use `web_service_priority` from YAML if provided
  # - Otherwise auto-calculate from 30000 upwards, in increments of 100
  rules_with_priority = {
    for index, service_config in local.combined_rules_list :
    service_config.service => merge(service_config, { priority = service_config.rule_priority != null ? service_config.rule_priority : 30000 + (index * 100) })
  }
}
