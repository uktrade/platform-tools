locals {

  secrets      = values(coalesce(var.service_config.secrets, {}))
  service_name = "${var.application}-${var.environment}-${var.service_config.name}"
  tags = {
    application = var.application
    environment = var.environment
    service     = var.service_config.name
    managed-by  = "DBT Platform - Service Terraform"
  }

  full_service_name    = "${var.application}-${var.environment}-${var.service_config.name}"
  vpc_name             = var.env_config[var.environment]["vpc"]
  web_service_required = var.service_config.type == "Load Balanced Web Service" ? 1 : 0

  central_log_group_arns        = jsondecode(data.aws_ssm_parameter.log-destination-arn.value)
  central_log_group_destination = var.environment == "prod" ? local.central_log_group_arns["prod"] : local.central_log_group_arns["dev"]

  ##############################
  # S3 EXTENSIONS — SAME ACCOUNT
  ##############################

  # 1) Select S3 extensions
  s3_extensions_all = {
    for name, ext in try(var.platform_extensions, {}) :
    name => ext
    if try(ext.type, "") == "s3" || try(ext.type, "") == "s3-policy"
  }

  # 2) Keep only S3 extensions that apply to this service
  s3_extensions_for_service = {
    for name, ext in local.s3_extensions_all :
    name => ext
    if contains(try(ext.services, []), "__all__") || contains(try(ext.services, []), var.service_config.name)
  }

  # 3) Merge "*" defaults with env-specific overrides
  s3_extensions_for_service_with_env_merged = {
    for name, ext in local.s3_extensions_for_service :
    name => merge(
      lookup(try(ext.environments, {}), "*", {}),
      lookup(try(ext.environments, {}), var.environment, {})
    )
  }

  # 4) Check if buckets are static
  is_s3_static = {
    for name, ext in local.s3_extensions_for_service :
    name => try(ext.serve_static_content, false)
  }

  # 5) Resolve s3 bucket names for static and NON-static buckets
  s3_bucket_name = {
    for name, ext in local.s3_extensions_for_service_with_env_merged :
    name => (
      local.is_s3_static[name]
      ? (var.environment == "prod" ? "${ext.bucket_name}.${var.application}.prod.uktrade.digital" : "${ext.bucket_name}.${var.environment}.${var.application}.uktrade.digital")
      : ext.bucket_name
    )
  }

  # 6) KMS alias only for NON-static buckets
  s3_kms_alias_for_s3_extension = {
    for name, ext in local.s3_extensions_for_service_with_env_merged :
    name => "alias/${var.application}-${var.environment}-${ext.bucket_name}-key"
    if !local.is_s3_static[name]
  }


  ###########################
  # S3 EXTENSIONS — CROSS-ENV
  ###########################

  # 1) Collect all S3 cross environment rules across all S3 extensions
  s3_cross_env_rules_list = flatten([
    for ext_name, ext in try(var.platform_extensions, {}) : [
      for bucket_env, envconf in try(ext.environments, {}) : [
        for access_name, access in try(envconf.cross_environment_service_access, {}) : {
          key         = "${ext_name}:${bucket_env}:${access_name}"
          type        = try(ext.type, null)
          service     = try(access.service, null)
          service_env = try(access.environment, null) # env of the service that wants S3 access
          bucket_env  = bucket_env                    # env that owns the S3 bucket
          is_static   = try(ext.serve_static_content, false)
          bucket_name = (try(ext.serve_static_content, false)
            ? (bucket_env == "prod"
              ? "${envconf.bucket_name}.${var.application}.prod.uktrade.digital"
            : "${envconf.bucket_name}.${bucket_env}.${var.application}.uktrade.digital")
            : envconf.bucket_name
          )
          bucket_account = try(var.env_config[bucket_env].accounts.deploy.id, null)
          read           = try(access.read, false)
          write          = try(access.write, false)
        }
      ]
    ]
  ])

  # 2) Validate cross env config, and filter out rules that don't apply to this service
  s3_cross_env_rules_for_this_service = {
    for rule in local.s3_cross_env_rules_list :
    rule.key => rule
    if(rule.type == "s3" || rule.type == "s3-policy")
    && rule.service == var.service_config.name
    && rule.service_env == var.environment
    && rule.bucket_name != null
    && rule.bucket_account != null
  }
}
