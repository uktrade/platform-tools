locals {
  tags = {
    application         = var.application
    copilot-application = var.application
    managed-by          = "DBT Platform - Terraform"
  }

  stage_config = yamldecode(file("${path.module}/stage_config.yml"))

  base_env_config = { for name, config in var.environment_config : name => merge(lookup(var.environment_config, "*", {}), config) if name != "*" }

  extracted_account_names_and_ids = toset(flatten([
    for env, env_config in local.base_env_config : [
      for account_type, account_details in env_config.accounts : {
        "name" = account_details.name,
        "id"   = account_details.id
      }
    ]
  ]))

  account_map = { for account in local.extracted_account_names_and_ids : account["name"] => account["id"] }

  # Convert the env config into a list and add env name and vpc / requires_approval from the environments config.
  environment_config = [for name, env in var.environments : merge(lookup(local.base_env_config, name, {}), env, { "name" = name })]

  triggers_another_pipeline         = var.pipeline_to_trigger != null
  triggered_pipeline_account_name   = local.triggers_another_pipeline ? var.all_pipelines[var.pipeline_to_trigger].account : null
  triggered_account_id              = local.triggers_another_pipeline ? local.account_map[local.triggered_pipeline_account_name] : null
  triggered_pipeline_codebuild_role = local.triggers_another_pipeline ? "arn:aws:iam::${local.triggered_account_id}:role/${var.application}-${var.pipeline_to_trigger}-environment-pipeline-codebuild" : null
  triggered_pipeline_environments   = local.triggers_another_pipeline ? [for name, config in var.all_pipelines[var.pipeline_to_trigger].environments : { "name" = name }] : null

  list_of_triggering_pipelines     = [for pipeline, config in var.all_pipelines : merge(config, { name = pipeline }) if lookup(config, "pipeline_to_trigger", null) == var.pipeline_name]
  set_of_triggering_pipeline_names = toset([for pipeline in local.list_of_triggering_pipelines : pipeline.name])
  triggering_pipeline_role_arns    = [for name in local.set_of_triggering_pipeline_names : "arn:aws:iam::${local.account_map[var.all_pipelines[name].account]}:role/${var.application}-${name}-environment-pipeline-codebuild"]

  triggered_by_another_pipeline      = length([for config in var.all_pipelines : true if lookup(config, "pipeline_to_trigger", null) == var.pipeline_name]) > 0
  triggering_pipeline_account_name   = local.triggered_by_another_pipeline ? one(local.list_of_triggering_pipelines).account : null
  triggering_account_id              = local.triggered_by_another_pipeline ? local.account_map[local.triggering_pipeline_account_name] : null
  triggering_pipeline_name           = local.triggered_by_another_pipeline ? one(local.list_of_triggering_pipelines).name : null
  triggering_pipeline_codebuild_role = local.triggered_by_another_pipeline ? "arn:aws:iam::${local.triggering_account_id}:role/${var.application}-${local.triggering_pipeline_name}-environment-pipeline-codebuild" : null

  current_codebuild_role_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.application}-${var.pipeline_name}-environment-pipeline-codebuild"

  initial_stages = [for env in local.environment_config : [
    # The first element of the inner list for an env is the Plan stage.
    {
      type : "plan",
      stage_name : "Plan-${env.name}",
      env : env.name,
      accounts : env.accounts,
      input_artifacts : ["build_output"],
      output_artifacts : ["${env.name}_terraform_plan"],
      configuration : {
        ProjectName : "${var.application}-${var.pipeline_name}-environment-pipeline-plan"
        PrimarySource : "build_output"
        EnvironmentVariables : jsonencode([
          { name : "APPLICATION", value : var.application },
          { name : "ENVIRONMENT", value : env.name },
          { name : "PIPELINE_NAME", value : var.pipeline_name },
          { name : "SLACK_CHANNEL_ID", value : var.slack_channel, type : "PARAMETER_STORE" },
          { name : "SLACK_REF", value : "#{slack.SLACK_REF}" },
          { name : "NEEDS_APPROVAL", value : lookup(env, "requires_approval", false) ? "yes" : "no" },
          { name : "SLACK_THREAD_ID", value : "#{variables.SLACK_THREAD_ID}" },
          { name : "PLATFORM_HELPER_VERSION_OVERRIDE", value : var.pinned_version != null ? var.pinned_version : "#{variables.PLATFORM_HELPER_VERSION_OVERRIDE}" },
        ])
      }
      namespace : "${env.name}-plan"
    },
    # The second element of the inner list for an env is the Approval stage if required, or the empty list otherwise.
    lookup(env, "requires_approval", false) ? [{
      type : "approve",
      stage_name : "Approve-${env.name}",
      env : "",
      input_artifacts : [],
      output_artifacts : [],
      configuration : {
        CustomData : "Review Terraform Plan"
        ExternalEntityLink : "https://${data.aws_region.current.region}.console.aws.amazon.com/codesuite/codebuild/${data.aws_caller_identity.current.account_id}/projects/${var.application}-${var.pipeline_name}-environment-pipeline-plan/build/#{${env.name}-plan.BUILD_ID}"
      },
      namespace : null
    }] : [],
    # The third element of the inner list for an env is the Apply stage.
    {
      type : "apply",
      env : env.name,
      stage_name : "Apply-${env.name}",
      accounts : env.accounts,
      input_artifacts : ["${env.name}_terraform_plan"],
      output_artifacts : [],
      configuration : {
        ProjectName : "${var.application}-${var.pipeline_name}-environment-pipeline-apply"
        PrimarySource : "${env.name}_terraform_plan"
        EnvironmentVariables : jsonencode([
          { name : "ENVIRONMENT", value : env.name },
          { name : "AWS_PROFILE_FOR_COPILOT", value : env.accounts.deploy.name },
          { name : "SLACK_CHANNEL_ID", value : var.slack_channel, type : "PARAMETER_STORE" },
          { name : "SLACK_REF", value : "#{slack.SLACK_REF}" },
          { name : "SLACK_THREAD_ID", value : "#{variables.SLACK_THREAD_ID}" },
          { name : "CURRENT_CODEBUILD_ROLE", value : local.current_codebuild_role_arn },
          local.triggered_by_another_pipeline ? { name : "TRIGGERING_ACCOUNT_CODEBUILD_ROLE", value : local.triggering_pipeline_codebuild_role } : null,
          local.triggered_by_another_pipeline ? { name : "TRIGGERING_ACCOUNT_AWS_PROFILE", value : local.triggering_pipeline_account_name } : null,
        ])
      },
      namespace : null
    }
    ]
  ]

  triggered_pipeline_account_role = local.triggers_another_pipeline ? "arn:aws:iam::${local.triggered_account_id}:role/${var.application}-${var.pipeline_to_trigger}-trigger-pipeline-from-${var.pipeline_name}" : null
  target_pipeline                 = local.triggers_another_pipeline ? "${var.application}-${var.pipeline_to_trigger}-environment-pipeline" : null

  all_stages = flatten(
    concat(local.initial_stages, local.triggers_another_pipeline ? [
      {
        type : "trigger",
        stage_name : "Trigger-Pipeline",
        input_artifacts : ["build_output"],
        output_artifacts : [],
        configuration : {
          ProjectName : "${var.application}-${var.pipeline_name}-environment-pipeline-trigger"
          PrimarySource : "build_output"
          EnvironmentVariables : jsonencode([
            { name : "TRIGGERED_ACCOUNT_ROLE_ARN", value : local.triggered_pipeline_account_role },
            { name : "TRIGGERED_PIPELINE_NAME", value : local.target_pipeline },
            { name : "TRIGGERED_PIPELINE_AWS_PROFILE", value : local.triggered_pipeline_account_name },
            { name : "SLACK_THREAD_ID", value : "#{variables.SLACK_THREAD_ID}" },
            { name : "SLACK_CHANNEL_ID", value : var.slack_channel, type : "PARAMETER_STORE" },
            { name : "SLACK_REF", value : "#{slack.SLACK_REF}" },
          ])
        },
        namespace : null
    }] : [])
  )

  dns_ids                   = tolist(toset(flatten([for stage in local.all_stages : lookup(stage, "accounts", null) != null ? [stage.accounts.dns.id] : []])))
  dns_account_assumed_roles = [for id in local.dns_ids : "arn:aws:iam::${id}:role/environment-pipeline-assumed-role"]


  # Merge in the stage specific config from the stage_config.yml file:
  stages = [for stage in local.all_stages : merge(stage, local.stage_config[stage["type"]])]

  account_region = "${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}"

  # cross account access does not allow the ListLayers action to be called to retrieve layer version dynamically, so hardcoding
  lambda_layer = "arn:aws:lambda:eu-west-2:763451185160:layer:python-requests:8"
}
