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
    for_each = each.value.environments
    content {
      name = "Deploy-Terraform-${stage.value.name}"
      on_failure {
        result = "ROLLBACK"
      }

      dynamic "action" {
        for_each = coalesce(stage.value.requires_approval, false) ? [1] : []
        content {
          name      = "Approve-${stage.value.name}"
          category  = "Approval"
          owner     = "AWS"
          provider  = "Manual"
          version   = "1"
          run_order = 1
        }
      }

      dynamic "action" {
        for_each = local.service_order_list
        content {
          name             = action.value.name
          category         = "Build"
          owner            = "AWS"
          provider         = "CodeBuild"
          input_artifacts  = ["deploy_source"]
          output_artifacts = []
          version          = "1"
          run_order        = action.value.order + 1

          configuration = {
            ProjectName = aws_codebuild_project.codebase_terraform_deploy.name
            EnvironmentVariables : jsonencode([
              { name : "APPLICATION", value : var.application },
              { name : "AWS_REGION", value : data.aws_region.current.name },
              { name : "AWS_ACCOUNT_ID", value : data.aws_caller_identity.current.account_id },
              { name : "ENVIRONMENT", value : stage.value.name },
              { name : "IMAGE_TAG", value : "#{variables.IMAGE_TAG}" },
              { name : "PIPELINE_EXECUTION_ID", value : "#{codepipeline.PipelineExecutionId}" },
              { name : "REPOSITORY_URL", value : local.repository_url },
              { name : "SERVICE", value : action.value.name },
              { name : "SLACK_CHANNEL_ID", value : var.slack_channel, type : "PARAMETER_STORE" },
            ])
          }
        }
      }

    }
  }

  dynamic "stage" {
    for_each = each.value.environments
    content {
      name = "Deploy-${stage.value.name}"
      on_failure {
        result = "ROLLBACK"
      }

      dynamic "action" {
        for_each = coalesce(stage.value.requires_approval, false) ? [1] : []
        content {
          name      = "Approve-${stage.value.name}"
          category  = "Approval"
          owner     = "AWS"
          provider  = "Manual"
          version   = "1"
          run_order = 1
        }
      }

      dynamic "action" {
        for_each = local.service_order_list
        content {
          name             = action.value.name
          category         = "Build"
          owner            = "AWS"
          provider         = "CodeBuild"
          input_artifacts  = ["deploy_source"]
          output_artifacts = []
          version          = "1"
          run_order        = action.value.order + 1

          configuration = {
            ProjectName = aws_codebuild_project.codebase_deploy.name
            EnvironmentVariables : jsonencode([
              { name : "APPLICATION", value : var.application },
              { name : "AWS_REGION", value : data.aws_region.current.name },
              { name : "AWS_ACCOUNT_ID", value : data.aws_caller_identity.current.account_id },
              { name : "ENVIRONMENT", value : stage.value.name },
              { name : "IMAGE_TAG", value : "#{variables.IMAGE_TAG}" },
              { name : "PIPELINE_EXECUTION_ID", value : "#{codepipeline.PipelineExecutionId}" },
              { name : "REPOSITORY_URL", value : local.repository_url },
              { name : "SERVICE", value : action.value.name },
              { name : "SLACK_CHANNEL_ID", value : var.slack_channel, type : "PARAMETER_STORE" },
            ])
          }
        }
      }

      dynamic "action" {
        for_each = coalesce(stage.value.requires_cache_invalidation, false) ? [1] : []
        content {
          name             = "InvalidateCache-${stage.value.name}"
          category         = "Build"
          owner            = "AWS"
          provider         = "CodeBuild"
          input_artifacts  = ["deploy_source"]
          output_artifacts = []
          version          = "1"
          run_order        = length(local.service_order_list) + 2

          configuration = {
            ProjectName = aws_codebuild_project.invalidate_cache[""].name
            EnvironmentVariables : jsonencode([
              { name : "CACHE_INVALIDATION_CONFIG", value : jsonencode(local.cache_invalidation_map) },
              { name : "APPLICATION", value : var.application },
              { name : "ENVIRONMENT", value : stage.value.name },
            ])
          }
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

  stage {
    name = "Deploy-Terraform"

    dynamic "action" {
      for_each = local.service_order_list
      content {
        name             = action.value.name
        category         = "Build"
        owner            = "AWS"
        provider         = "CodeBuild"
        input_artifacts  = ["deploy_source"]
        output_artifacts = []
        version          = "1"
        run_order        = action.value.order + 1

        configuration = {
          ProjectName = aws_codebuild_project.codebase_terraform_deploy.name
          EnvironmentVariables : jsonencode([
            { name : "APPLICATION", value : var.application },
            { name : "AWS_REGION", value : data.aws_region.current.name },
            { name : "AWS_ACCOUNT_ID", value : data.aws_caller_identity.current.account_id },
            { name : "ENVIRONMENT", value : "#{variables.ENVIRONMENT}" },
            { name : "IMAGE_TAG", value : "#{variables.IMAGE_TAG}" },
            { name : "PIPELINE_EXECUTION_ID", value : "#{codepipeline.PipelineExecutionId}" },
            { name : "REPOSITORY_URL", value : local.repository_url },
            { name : "SERVICE", value : action.value.name },
            { name : "SLACK_CHANNEL_ID", value : var.slack_channel, type : "PARAMETER_STORE" },
          ])
        }
      }
    }

  }

  stage {
    name = "Deploy"

    dynamic "action" {
      for_each = local.service_order_list
      content {
        name             = action.value.name
        category         = "Build"
        owner            = "AWS"
        provider         = "CodeBuild"
        input_artifacts  = ["deploy_source"]
        output_artifacts = []
        version          = "1"
        run_order        = action.value.order + 1

        configuration = {
          ProjectName = aws_codebuild_project.codebase_deploy.name
          EnvironmentVariables : jsonencode([
            { name : "APPLICATION", value : var.application },
            { name : "AWS_REGION", value : data.aws_region.current.name },
            { name : "AWS_ACCOUNT_ID", value : data.aws_caller_identity.current.account_id },
            { name : "ENVIRONMENT", value : "#{variables.ENVIRONMENT}" },
            { name : "IMAGE_TAG", value : "#{variables.IMAGE_TAG}" },
            { name : "PIPELINE_EXECUTION_ID", value : "#{codepipeline.PipelineExecutionId}" },
            { name : "REPOSITORY_URL", value : local.repository_url },
            { name : "SERVICE", value : action.value.name },
            { name : "SLACK_CHANNEL_ID", value : var.slack_channel, type : "PARAMETER_STORE" },
          ])
        }
      }
    }

    dynamic "action" {
      for_each = toset(local.cache_invalidation_enabled ? [""] : [])
      content {
        name             = "InvalidateCache"
        category         = "Build"
        owner            = "AWS"
        provider         = "CodeBuild"
        input_artifacts  = ["deploy_source"]
        output_artifacts = []
        version          = "1"
        run_order        = length(local.service_order_list) + 2

        configuration = {
          ProjectName = aws_codebuild_project.invalidate_cache[""].name
          EnvironmentVariables : jsonencode([
            { name : "CACHE_INVALIDATION_CONFIG", value : jsonencode(local.cache_invalidation_map) },
            { name : "APPLICATION", value : var.application },
            { name : "ENVIRONMENT", value : "#{variables.ENVIRONMENT}" },
          ])
        }
      }
    }
  }

  tags = local.tags
}
