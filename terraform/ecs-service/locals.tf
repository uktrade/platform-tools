locals {
  tags = {
    application = var.application
    environment = var.environment
    service     = var.service_config.name
    managed-by  = "DBT Platform - Service Terraform"
  }

  full_service_name    = "${var.application}-${var.environment}-${var.service_config.name}"
  vpc_name             = var.env_config[var.environment]["vpc"]
  secrets              = values(coalesce(var.service_config.secrets, {}))
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


  ##########################################################
  # CONTAINER DEFINITIONS TEMPLATE (USED IN PLATFORM HELPER)
  ##########################################################

  # TODO - Remove COPILOT_ vars once nopilot is complete. Check ALL codebases for any references to them before removal.
  required_env_vars = {
    COPILOT_APPLICATION_NAME            = var.application
    COPILOT_ENVIRONMENT_NAME            = var.environment
    COPILOT_SERVICE_NAME                = var.service_config.name
    COPILOT_SERVICE_DISCOVERY_ENDPOINT  = "${var.environment}.${var.application}.services.local"
    PLATFORM_APPLICATION_NAME           = var.application
    PLATFORM_ENVIRONMENT_NAME           = var.environment
    PLATFORM_SERVICE_NAME               = var.service_config.name
    PLATFORM_SERVICE_DISCOVERY_ENDPOINT = "${var.environment}.${var.application}.services.local"
  }

  default_container_config = {
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = "/platform/ecs/service/${var.application}/${var.environment}/${var.service_config.name}"
        awslogs-region        = data.aws_region.current.region
        awslogs-stream-prefix = "platform"
      }
    }
  }

  main_port_mappings = (
    var.service_config.type == "Load Balanced Web Service" && try(var.service_config.image.port, null) != null
    ) ? [
    merge(
      { containerPort = var.service_config.image.port, protocol = "tcp" },
      (
        try(var.service_config.http.target_container, "") == var.service_config.name
      ) ? { name = "target" } : {}
    )
  ] : []

  depends_on_map = {
    for k, v in coalesce(try(var.service_config.image.depends_on, {}), {}) :
    k => upper(v)
  }

  main_container = merge(
    local.default_container_config,
    {
      name      = var.service_config.name
      image     = var.service_config.image.location
      essential = true
      environment = [
        for k, v in merge(try(var.service_config.variables, {}), local.required_env_vars) :
        { name = k, value = tostring(v) }
      ]
      secrets = [
        for k, v in coalesce(var.service_config.secrets, {}) :
        { name = k, valueFrom = v }
      ]
      readonlyRootFilesystem = try(var.service_config.storage.readonly_fs, false)
      portMappings           = local.main_port_mappings
      mountPoints = concat([
        { sourceVolume = "path-tmp", containerPath = "/tmp" }
        ], [
        for path in coalesce(var.service_config.storage.writable_directories, []) :
        { sourceVolume = "path${replace(path, "/", "-")}", containerPath = path }
      ])
      # Ensure main container always starts last
      dependsOn = concat([
        for sidecar in keys(coalesce(var.service_config.sidecars, {})) : {
          containerName = sidecar
          condition     = lookup(local.depends_on_map, sidecar, "START")
        }
        ], [
        {
          containerName = "writable_directories_permission"
          condition     = "SUCCESS"
        }
        ]
      )
    },
    var.service_config.type == "Backend Service" && try(var.service_config.entrypoint, null) != null ?
    { entryPoint = var.service_config.entrypoint } : {},
  )

  permissions_container = merge(local.default_container_config, {
    name      = "writable_directories_permission"
    image     = "public.ecr.aws/docker/library/alpine:latest"
    essential = false
    command = [
      "/bin/sh",
      "-c",
      "chmod -R a+w /tmp && chown -R 1002:1000 ${join(" ", coalesce(var.service_config.storage.writable_directories, []))}"
    ]
    mountPoints = concat([
      { sourceVolume = "path-tmp", readOnly = false, containerPath = "/tmp" }
      ], [
      for path in coalesce(var.service_config.storage.writable_directories, []) :
      { sourceVolume = "path${replace(path, "/", "-")}", readOnly = false, containerPath = path }
    ])
  })

  sidecar_containers = [
    for sidecar_name, sidecar in coalesce(var.service_config.sidecars, {}) : merge(
      local.default_container_config,
      {
        name      = sidecar_name
        image     = sidecar.image
        essential = coalesce(sidecar.essential, true)
        environment = [
          for k, v in merge(coalesce(sidecar.variables, {}), local.required_env_vars) :
          { name = k, value = tostring(v) }
        ]
        secrets = [
          for k, v in coalesce(sidecar.secrets, {}) : { name = k, valueFrom = v }
        ]
        portMappings = sidecar.port != null ? [
          merge(
            { containerPort = sidecar.port, protocol = "tcp" },
            # Add Service Connect target port name when this sidecar is the declared target
            (
              var.service_config.type == "Load Balanced Web Service" &&
              try(var.service_config.http.target_container, "") == sidecar_name
            )
            ? { name = "target" }
            : {}
          )
        ] : []
      },
    )
  ]

  container_definitions_list = concat(
    [local.main_container],
    local.sidecar_containers,
    [local.permissions_container]
  )

  writable_volumes = [
    for path in coalesce(var.service_config.storage.writable_directories, []) :
    { "name" : "path${replace(path, "/", "-")}", "host" : {} }
  ]

  task_definition_json = jsonencode({
    family                  = "${var.application}-${var.environment}-${var.service_config.name}-task-def"
    taskRoleArn             = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.application}-${var.environment}-${var.service_config.name}-ecs-task-role"
    executionRoleArn        = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.application}-${var.environment}-${var.service_config.name}-ecs-task-execution-role"
    networkMode             = "awsvpc"
    containerDefinitions    = local.container_definitions_list
    volumes                 = concat([{ "name" : "path-tmp", "host" : {} }], local.writable_volumes)
    placementConstraints    = []
    requiresCompatibilities = ["FARGATE"]
    cpu                     = tostring(var.service_config.cpu)
    memory                  = tostring(var.service_config.memory)
    tags = [
      { "key" : "application", "value" : var.application },
      { "key" : "environment", "value" : var.environment },
      { "key" : "service", "value" : var.service_config.name },
      { "key" : "managed-by", "value" : "Platform Helper" },
    ]
  })

}
