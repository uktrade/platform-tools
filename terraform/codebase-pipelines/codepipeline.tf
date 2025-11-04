resource "aws_codepipeline" "codebase_pipeline" {
  for_each       = local.pipeline_map
  name           = "${var.application}-${var.codebase}-${each.value.name}-codebase"
  role_arn       = aws_iam_role.codebase_deploy_pipeline.arn
  depends_on     = [aws_iam_role_policy.artifact_store_access_for_codebase_pipeline]
  pipeline_type  = "V2"
  execution_mode = "QUEUED"

  variable {
    name          = "IMAGE_TAG"
    default_value = each.value.image_tag
    description   = "Tagged image in ECR to deploy"
  }

  artifact_store {
    location = aws_s3_bucket.artifact_store.bucket
    type     = "S3"

    encryption_key {
      id   = aws_kms_key.artifact_store_kms_key.arn
      type = "KMS"
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
      output_artifacts = ["deploy_source"]

      configuration = {
        ConnectionArn    = data.external.codestar_connections.result["ConnectionArn"]
        FullRepositoryId = var.deploy_repository != null ? var.deploy_repository : "uktrade/${var.application}-deploy"
        BranchName       = var.deploy_repository_branch
        DetectChanges    = false
      }
    }
  }


  dynamic "stage" {
    for_each = toset(local.platform_deployment_enabled ? [""] : [])
    content {
      name = "Install-Tools"
      action {
        name             = "InstallTools"
        category         = "Build"
        owner            = "AWS"
        provider         = "CodeBuild"
        version          = "1"
        input_artifacts  = ["deploy_source"]
        output_artifacts = ["tools_output"]

        configuration = {
          ProjectName   = aws_codebuild_project.codebase_install_tools[""].name
          PrimarySource = "deploy_source"
          EnvironmentVariables : jsonencode([
            { name : "APPLICATION", value : var.application },
            { name : "AWS_REGION", value : data.aws_region.current.region },
            { name : "AWS_ACCOUNT_ID", value : data.aws_caller_identity.current.account_id },
            { name : "PIPELINE_NAME", value : var.codebase },
            { name : "REPOSITORY", value : var.repository },
            { name : "SLACK_CHANNEL_ID", value : var.slack_channel, type : "PARAMETER_STORE" },
            { name : "CODESTAR_CONNECTION_ARN", value : data.external.codestar_connections.result["ConnectionArn"] },
          ])
        }
      }
    }
  }

  dynamic "stage" {
    for_each = each.value.stages
    content {
      name = stage.value.name
      on_failure {
        result = try(stage.value.on_failure, "ROLLBACK")
      }

      dynamic "action" {
        # Sort to prevent actions with the same run order causing unnecessary terraform changes
        for_each = [
          for n in sort([for a in stage.value.actions : "${a.order}-${a.name}"]) :
          lookup({ for a in stage.value.actions : "${a.order}-${a.name}" => a }, n)
        ]

        content {
          name             = action.value.name
          category         = try(action.value.category, "Build")
          provider         = try(action.value.provider, "CodeBuild")
          input_artifacts  = try(action.value.input_artifacts, ["deploy_source"])
          output_artifacts = []
          owner            = "AWS"
          version          = "1"
          run_order        = action.value.order
          configuration    = action.value.configuration
        }
      }
    }
  }

  tags = local.tags
}


resource "aws_codepipeline" "manual_release_pipeline" {
  name           = "${var.application}-${var.codebase}-manual-release"
  role_arn       = aws_iam_role.codebase_deploy_pipeline.arn
  pipeline_type  = "V2"
  execution_mode = "QUEUED"

  variable {
    name          = "IMAGE_TAG"
    default_value = "NONE"
    description   = "Tagged image in ECR to deploy"
  }

  variable {
    name          = "ENVIRONMENT"
    default_value = "NONE"
    description   = "Name of the environment to deploy to"
  }

  artifact_store {
    location = aws_s3_bucket.artifact_store.bucket
    type     = "S3"

    encryption_key {
      id   = aws_kms_key.artifact_store_kms_key.arn
      type = "KMS"
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
      output_artifacts = ["deploy_source"]

      configuration = {
        ConnectionArn    = data.external.codestar_connections.result["ConnectionArn"]
        FullRepositoryId = var.deploy_repository != null ? var.deploy_repository : "uktrade/${var.application}-deploy"
        BranchName       = var.deploy_repository_branch
        DetectChanges    = false
      }
    }
  }

  dynamic "stage" {
    for_each = toset(local.platform_deployment_enabled ? [""] : [])
    content {
      name = "Install-Tools"
      action {
        name             = "InstallTools"
        category         = "Build"
        owner            = "AWS"
        provider         = "CodeBuild"
        version          = "1"
        input_artifacts  = ["deploy_source"]
        output_artifacts = ["tools_output"]

        configuration = {
          ProjectName   = aws_codebuild_project.codebase_install_tools[""].name
          PrimarySource = "deploy_source"
          EnvironmentVariables : jsonencode([
            { name : "APPLICATION", value : var.application },
            { name : "AWS_REGION", value : data.aws_region.current.region },
            { name : "AWS_ACCOUNT_ID", value : data.aws_caller_identity.current.account_id },
            { name : "PIPELINE_NAME", value : var.codebase },
            { name : "REPOSITORY", value : var.repository },
            { name : "SLACK_CHANNEL_ID", value : var.slack_channel, type : "PARAMETER_STORE" },
            { name : "CODESTAR_CONNECTION_ARN", value : data.external.codestar_connections.result["ConnectionArn"] },
          ])
        }
      }
    }
  }

  stage {
    name = "Deploy"

    dynamic "action" {
      # Sort to prevent actions with the same run order causing unnecessary terraform changes
      for_each = [
        for n in sort([for a in local.manual_pipeline_actions_map : "${a.order}-${a.name}"]) :
        lookup({ for a in local.manual_pipeline_actions_map : "${a.order}-${a.name}" => a }, n)
      ]

      content {
        name             = action.value.name
        category         = try(action.value.category, "Build")
        provider         = try(action.value.provider, "CodeBuild")
        input_artifacts  = try(action.value.input_artifacts, ["deploy_source"])
        output_artifacts = []
        owner            = "AWS"
        version          = "1"
        run_order        = action.value.order
        configuration    = action.value.configuration
      }
    }
  }

  tags = local.tags
}
