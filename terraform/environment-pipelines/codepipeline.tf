data "aws_ssm_parameter" "connection_name" {
  name = "/codestarconnection/name"
}

data "external" "codestar_connections" {
  program = ["bash", "-c", <<-EOT
    aws codeconnections list-connections --provider-type GitHub --query "Connections[?ConnectionName=='${data.aws_ssm_parameter.connection_name.value}' && ConnectionStatus=='AVAILABLE'] | [0]" --output json
  EOT
  ]
}

resource "aws_codepipeline" "environment_pipeline" {
  name          = "${var.application}-${var.pipeline_name}-environment-pipeline"
  role_arn      = aws_iam_role.environment_pipeline_codepipeline.arn
  depends_on    = [aws_iam_role_policy.artifact_store_access_for_environment_codebuild]
  pipeline_type = "V2"

  variable {
    name          = "SLACK_THREAD_ID"
    default_value = "NONE"
    description   = "This can be set by a triggering pipeline to continue an existing message thread"
  }

  dynamic "variable" {
    for_each = var.pinned_version == null ? [1] : []
    content {
      name          = "PLATFORM_HELPER_VERSION_OVERRIDE"
      default_value = "NONE"
      description   = "Override the platform-helper default version specified in platform-config"
    }
  }

  artifact_store {
    location = aws_s3_bucket.artifact_store.bucket
    type     = "S3"

    encryption_key {
      id   = aws_kms_key.artifact_store_kms_key.arn
      type = "KMS"
    }
  }

  trigger {
    provider_type = "CodeStarSourceConnection"
    git_configuration {
      source_action_name = "GitCheckout"
      push {
        branches {
          includes = [
            var.trigger_on_push ? var.branch : "NO_TRIGGER"
          ]
        }
      }
    }
  }

  stage {
    name = "Source"

    action {
      name             = "GitCheckout"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["project_deployment_source"]

      configuration = {
        ConnectionArn    = data.external.codestar_connections.result["ConnectionArn"]
        FullRepositoryId = var.repository
        BranchName       = var.branch
        DetectChanges    = var.trigger_on_push
      }
    }
  }

  stage {
    name = "Install-Build-Tools"

    action {
      name             = "InstallTools"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      input_artifacts  = ["project_deployment_source"]
      output_artifacts = ["build_output"]
      version          = "1"
      namespace        = "slack"

      configuration = {
        ProjectName   = "${var.application}-${var.pipeline_name}-environment-pipeline-build"
        PrimarySource = "project_deployment_source"
        EnvironmentVariables : jsonencode([
          { name : "APPLICATION", value : var.application },
          { name : "AWS_REGION", value : data.aws_region.current.region },
          { name : "AWS_ACCOUNT_ID", value : data.aws_caller_identity.current.account_id },
          { name : "PIPELINE_NAME", value : var.pipeline_name },
          { name : "REPOSITORY", value : var.repository },
          { name : "SLACK_CHANNEL_ID", value : var.slack_channel, type : "PARAMETER_STORE" },
          { name : "SLACK_THREAD_ID", value : "#{variables.SLACK_THREAD_ID}" },
          { name : "PLATFORM_HELPER_VERSION_OVERRIDE", value : var.pinned_version != null ? var.pinned_version : "#{variables.PLATFORM_HELPER_VERSION_OVERRIDE}" },
          { name : "CODESTAR_CONNECTION_ARN", value : data.external.codestar_connections.result["ConnectionArn"] },
        ])
      }
    }
  }

  dynamic "stage" {
    for_each = local.stages
    content {
      name = stage.value.stage_name

      action {
        name             = stage.value.name
        category         = stage.value.category
        owner            = stage.value.owner
        provider         = stage.value.provider
        input_artifacts  = stage.value.input_artifacts
        output_artifacts = stage.value.output_artifacts
        version          = "1"
        configuration    = stage.value.configuration
        namespace        = stage.value.namespace
      }
    }
  }

  tags = merge(
    local.tags,
    {
      platform-version = var.pinned_version != null ? var.pinned_version : "See default_version in platform-config.yml"
    }
  )
}
