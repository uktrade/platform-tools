locals {
  tags = {
    application         = var.application
    copilot-application = var.application
    managed-by          = "DBT Platform - Terraform"
  }

  stage_config = yamldecode(file("${path.module}/stage_config.yml"))

  base_env_config = { for name, config in var.env_config : name => merge(lookup(var.env_config, "*", {}), config) if name != "*" }

  # Convert the env config into a list and add env name and vpc / requires_approval from the environments config.
  environment_config = [for name, env in var.environments : merge(lookup(local.base_env_config, name, {}), env, { "name" = name })]

  deploy_account_ids = distinct(flatten([
    for env in local.environment_config : [for name, account in env.accounts : account.id if name == "deploy"]
  ]))

  current_codebuild_role_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.application}-${var.pipeline_name}-environment-pipeline-codebuild"

  all_stages = flatten([for env in local.environment_config : [
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
          { name : "PLATFORM_HELPER_VERSION_OVERRIDE", value : "#{variables.PLATFORM_HELPER_VERSION_OVERRIDE}" },
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
        ExternalEntityLink : "https://${data.aws_region.current.name}.console.aws.amazon.com/codesuite/codebuild/${data.aws_caller_identity.current.account_id}/projects/${var.application}-${var.pipeline_name}-environment-pipeline-plan/build/#{${env.name}-plan.BUILD_ID}"
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
          { name : "CURRENT_CODEBUILD_ROLE", value : local.current_codebuild_role_arn }
        ])
      },
      namespace : null
    }
    ]
  ])

  dns_ids                   = tolist(toset(flatten([for stage in local.all_stages : lookup(stage, "accounts", null) != null ? [stage.accounts.dns.id] : []])))
  dns_account_assumed_roles = [for id in local.dns_ids : "arn:aws:iam::${id}:role/environment-pipeline-assumed-role"]


  # Merge in the stage specific config from the stage_config.yml file:
  stages = [for stage in local.all_stages : merge(stage, local.stage_config[stage["type"]])]

  account_region = "${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}"

  # cross account access does not allow the ListLayers action to be called to retrieve layer version dynamically, so hardcoding
  lambda_layer = "arn:aws:lambda:eu-west-2:763451185160:layer:python-requests:8"
}
