locals {
  tags = {
    application         = var.application
    copilot-application = var.application
    managed-by          = "DBT Platform - Terraform"
  }

  account_region = "${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}"

  ecr_name                    = "${var.application}/${var.codebase}"
  private_repo_url            = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.region}.amazonaws.com"
  is_additional_repo_public   = var.additional_ecr_repository != null ? strcontains(var.additional_ecr_repository, "public.ecr.aws") : false
  additional_ecr_url          = var.additional_ecr_repository != null ? local.is_additional_repo_public ? var.additional_ecr_repository : "${local.private_repo_url}/${var.additional_ecr_repository}" : null
  repository_url              = coalesce(local.additional_ecr_url, "${local.private_repo_url}/${local.ecr_name}")
  additional_private_repo_arn = var.additional_ecr_repository != null && !local.is_additional_repo_public ? "arn:aws:ecr:${local.account_region}:repository/${var.additional_ecr_repository}" : ""

  pipeline_branches = distinct([
    for pipeline in var.pipelines : pipeline.branch if lookup(pipeline, "branch", null) != null
  ])

  tagged_pipeline = length([for pipeline in var.pipelines : true if lookup(pipeline, "tag", null) == true]) > 0

  base_env_config = {
    for name, config in var.env_config : name => {
      account_id : lookup(lookup(lookup(merge(lookup(var.env_config, "*", {}), config), "accounts", {}), "deploy", {}), "id", {}),
      account_name : lookup(lookup(lookup(merge(lookup(var.env_config, "*", {}), config), "accounts", {}), "deploy", {}), "name", {}),
      dns_account : lookup(lookup(lookup(merge(lookup(var.env_config, "*", {}), config), "accounts", {}), "dns", {}), "id", {}),
      service_deployment_mode : lookup(merge(lookup(var.env_config, "*", {}), config), "service-deployment-mode", "copilot")
    } if name != "*"
  }

  deploy_account_ids = distinct([for env in local.base_env_config : env.account_id])

  dns_account_ids = distinct([for env in local.base_env_config : env.dns_account])

  cache_invalidation_assumed_roles = [for id in local.dns_account_ids : "arn:aws:iam::${id}:role/cloudfront-invalidation-assumed-role"]

  environments_requiring_cache_invalidation = distinct([for d in try(values(var.cache_invalidation.domains), []) : d.environment])

  cache_invalidation_enabled = length(local.environments_requiring_cache_invalidation) > 0

  default_variables = [
    { name : "APPLICATION", value : var.application },
    { name : "AWS_REGION", value : data.aws_region.current.region },
    { name : "AWS_ACCOUNT_ID", value : data.aws_caller_identity.current.account_id },
    { name : "REPOSITORY_URL", value : local.repository_url },
    { name : "SLACK_CHANNEL_ID", value : var.slack_channel, type : "PARAMETER_STORE" },
    { name : "PIPELINE_EXECUTION_ID", value : "#{codepipeline.PipelineExecutionId}" },
    { name : "IMAGE_TAG", value : "#{variables.IMAGE_TAG}" },
  ]

  pipeline_map = {
    for id, val in var.pipelines : id => {
      name : val.name,
      branch : val.branch,
      image_tag : var.requires_image_build ? coalesce(val.tag, false) ? "tag-latest" : "branch-${replace(val.branch, "/", "-")}" : "latest",
      stages : flatten([for env in val.environments : concat(
        # Approval
        coalesce(env.requires_approval, false) ?
        [{
          name : "Approve-${env.name}",
          on_failure : "FAIL",
          actions : concat(local.base_env_config[env.name].service_deployment_mode != "copilot" ? [for svc in local.service_order_list : {
            name : "terraform-plan-${svc.name}",
            input_artifacts : ["tools_output"],
            order : 1,
            configuration : {
              ProjectName   = aws_codebuild_project.codebase_service_terraform_plan[""].name
              PrimarySource = "tools_output"
              EnvironmentVariables : jsonencode(concat(local.default_variables, [
                { name : "ENVIRONMENT", value : env.name },
                { name : "SERVICE", value : svc.name },
              ]))
            }
            }] : [], [{
            name : "manual-approval",
            order : 2,
            category : "Approval",
            provider : "Manual",
            input_artifacts : [],
            configuration : {
              CustomData : "Review the Terraform plan for ${length(local.service_order_list)} service(s)"
            }
          }])
        }] : [],
        # Deployment
        [{
          name : "Deploy-${env.name}",
          actions : concat(
            flatten([for svc in local.service_order_list : concat(
              local.base_env_config[env.name].service_deployment_mode != "copilot" ? [{
                name : "terraform-apply-${svc.name}",
                input_artifacts : ["tools_output"],
                order : svc.order,
                configuration = {
                  ProjectName   = aws_codebuild_project.codebase_service_terraform[""].name
                  PrimarySource = "tools_output"
                  EnvironmentVariables : jsonencode(concat(local.default_variables, [
                    { name : "ENVIRONMENT", value : env.name },
                    { name : "SERVICE", value : svc.name },
                  ]))
                }
              }] : [],
              local.base_env_config[env.name].service_deployment_mode != "copilot" ? [{
                name : "platform-deploy-${svc.name}",
                order : svc.order + 1,
                input_artifacts : ["tools_output"],
                configuration = {
                  ProjectName   = aws_codebuild_project.codebase_deploy_platform[""].name
                  PrimarySource = "tools_output"
                  EnvironmentVariables : jsonencode(concat(local.default_variables, [
                    { name : "ENVIRONMENT", value : env.name },
                    { name : "SERVICE", value : svc.name },
                  ]))
                }
              }] : [],
              local.base_env_config[env.name].service_deployment_mode != "platform" ? [{
                name : "copilot-deploy-${svc.name}",
                order : svc.order + 1,
                configuration = {
                  ProjectName = aws_codebuild_project.codebase_deploy[""].name
                  EnvironmentVariables : jsonencode(concat(local.default_variables, [
                    { name : "ENVIRONMENT", value : env.name },
                    { name : "SERVICE", value : svc.name },
                  ]))
                }
              }] : [],
            )]),
            local.base_env_config[env.name].service_deployment_mode != "copilot" &&
            local.base_env_config[env.name].service_deployment_mode != null ?
            [{
              name : "update-alb-rules",
              order : max([for svc in local.service_order_list : svc.order]...) + 2,
              input_artifacts : ["tools_output"],
              configuration = {
                ProjectName   = aws_codebuild_project.codebase_update_alb_rules.name
                PrimarySource = "tools_output"
                EnvironmentVariables : jsonencode([
                  { name : "APPLICATION", value : var.application },
                  { name : "ENVIRONMENT", value : env.name },
                  { name : "AWS_REGION", value : data.aws_region.current.region },
                  { name : "AWS_ACCOUNT_ID", value : data.aws_caller_identity.current.account_id },
                ])
              }
            }] : [],
            contains(local.environments_requiring_cache_invalidation, env.name) ? [{
              name : "invalidate-cache",
              order : max([for svc in local.service_order_list : svc.order]...) + 2,
              configuration = {
                ProjectName = aws_codebuild_project.invalidate_cache[""].name
                EnvironmentVariables : jsonencode([
                  { name : "CACHE_INVALIDATION_CONFIG", value : jsonencode(local.cache_invalidation_map) },
                  { name : "APPLICATION", value : var.application },
                  { name : "ENVIRONMENT", value : env.name },
                ])
              }
            }] : [],
          )
        }]
      )])
    }
  }

  manual_pipeline_actions_map = concat(
    flatten([for svc in local.service_order_list : concat(
      local.platform_deployment_enabled ? [{
        name : "terraform-apply-${svc.name}",
        order : svc.order,
        input_artifacts : ["tools_output"],
        configuration = {
          ProjectName   = aws_codebuild_project.codebase_service_terraform[""].name
          PrimarySource = "tools_output"
          EnvironmentVariables : jsonencode(concat(local.default_variables, [
            { name : "ENVIRONMENT", value : "#{variables.ENVIRONMENT}" },
            { name : "SERVICE", value : svc.name },
          ]))
        }
      }] : [],
      local.platform_deployment_enabled ? [{
        name : "platform-deploy-${svc.name}",
        order : svc.order + 1,
        input_artifacts : ["tools_output"],
        configuration = {
          ProjectName   = aws_codebuild_project.codebase_deploy_platform[""].name
          PrimarySource = "tools_output"
          EnvironmentVariables : jsonencode(concat(local.default_variables, [
            { name : "ENVIRONMENT", value : "#{variables.ENVIRONMENT}" },
            { name : "SERVICE", value : svc.name },
          ]))
        }
      }] : [],
      local.copilot_deployment_enabled ? [{
        name : "copilot-deploy-${svc.name}",
        order : svc.order + 1,
        configuration = {
          ProjectName = aws_codebuild_project.codebase_deploy[""].name
          EnvironmentVariables : jsonencode(concat(local.default_variables, [
            { name : "ENVIRONMENT", value : "#{variables.ENVIRONMENT}" },
            { name : "SERVICE", value : svc.name },
          ]))
        }
      }] : [],
    )]),
    local.base_env_config[env.name].service_deployment_mode != "copilot" &&
    local.base_env_config[env.name].service_deployment_mode != null ?
    [{
      name : "update-alb-rules",
      order : max([for svc in local.service_order_list : svc.order]...) + 2,
      input_artifacts : ["tools_output"],
      configuration = {
        ProjectName   = aws_codebuild_project.codebase_update_alb_rules.name
        PrimarySource = "tools_output"
        EnvironmentVariables : jsonencode([
          { name : "APPLICATION", value : var.application },
          { name : "ENVIRONMENT", value : "#{variables.ENVIRONMENT}" },
          { name : "AWS_REGION", value : data.aws_region.current.region },
          { name : "AWS_ACCOUNT_ID", value : data.aws_caller_identity.current.account_id },
        ])
      }
    }] : [],
    local.cache_invalidation_enabled ? [{
      name : "invalidate-cache",
      order : max([for svc in local.service_order_list : svc.order]...) + 2,
      configuration = {
        ProjectName = aws_codebuild_project.invalidate_cache[""].name
        EnvironmentVariables : jsonencode([
          { name : "CACHE_INVALIDATION_CONFIG", value : jsonencode(local.cache_invalidation_map) },
          { name : "APPLICATION", value : var.application },
          { name : "ENVIRONMENT", value : "#{variables.ENVIRONMENT}" },
        ])
      }
    }] : [],
  )

  cache_invalidation_map = tomap({
    for env in local.environments_requiring_cache_invalidation : env => {
      for domain, data in var.cache_invalidation.domains : domain => data.paths if data.environment == env
    }
  })

  services = sort(flatten([
    for run_group in var.services : [for service in flatten(values(run_group)) : service]
  ]))

  service_order_list = flatten([
    for index, group in var.services : [
      for key, services in group : [
        for sorted_service in local.services : [
          for service in services : {
            name  = service
            order = index + 1
          } if service == sorted_service
        ]
      ]
    ]
  ])

  # Set to true if any environment contains a service-deployment-mode whose value is not 'copilot'
  platform_deployment_enabled = anytrue([for env in local.base_env_config : true if env.service_deployment_mode != "copilot"])

  # Set to true if any environment contains a service-deployment-mode whose value is not 'platform'
  copilot_deployment_enabled = anytrue([for env in local.base_env_config : true if env.service_deployment_mode != "platform"])

}
