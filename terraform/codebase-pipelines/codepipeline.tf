resource "aws_codepipeline" "codebase_pipeline" {
  for_each       = local.pipeline_map
  name           = "${var.application}-${var.codebase}-${each.value.name}-codebase"
  role_arn       = aws_iam_role.codebase_deploy_pipeline.arn
  depends_on     = [aws_iam_role_policy.artifact_store_access_for_codebase_pipeline]
  pipeline_type  = "V2"
  execution_mode = "QUEUED"

  variable {
    name          = "IMAGE_TAG"
    default_value = var.requires_image_build ? coalesce(each.value.tag, false) ? "tag-latest" : "branch-${each.value.branch}" : "latest"
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
        for_each = coalesce(stage.value.requires_approval, false) ? [1] : []
        # TODO instead of requires_approval, we need requires_cache_invalidation here.
        # stage.value is one of the environments in pipeline_map
        # -> need to resolve a value within pipeline map that is true only if that environment is listed in caching config, or if we are defaulting to all environments
        content {
          name      = "InvalidateCache-${stage.value.name}"
          category         = "Build"
          owner            = "AWS"
          provider         = "CodeBuild"
          input_artifacts  = ["deploy_source"]
          output_artifacts = []
          version          = "1"
          run_order        = length(local.service_order_list) + 2 #TODO should depend on if there was a requires action or not?

          configuration = {
            ProjectName = aws_codebuild_project.invalidate_cache.name
            EnvironmentVariables : jsonencode([
              { name : "CONFIG_JSON", value : var.application }, #TODO pass in cache invalidation object for specific environment
              { name : "APPLICATION", value : var.application },
              { name : "ENVIRONMENT", value : stage.value.name },
              { name : "DNS_ACCOUNT_ID", value : local.base_env_config[stage.value.name].dns_account },
              # { name : "ENV_CONFIG", value : var.env_config },
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
    name = "Deploy"

    dynamic "action" {
      for_each = true ? [1] : [] 
      #TODO replace requires_approval with requires_cache_invalidation
      #TODO requires_cache_invalidation is true here if *ANY* environment requires it - e.g. if the cache_invalidation config block appears at all
      content {
        name      = "InvalidateCache"
        category         = "Build"
        owner            = "AWS"
        provider         = "CodeBuild"
        input_artifacts  = ["deploy_source"]
        output_artifacts = []
        version          = "1"
        run_order        = length(local.service_order_list) + 2 #TODO should depend on if there was a requires action or not?

        configuration = {
          ProjectName = aws_codebuild_project.invalidate_cache.name #TODO Note - Could use a different project/buildspec initially to avoid breaking the working one?
          EnvironmentVariables : jsonencode([
            { name : "CONFIG_JSON", value : "foo" }, #TODO pass in a cache_invalidation_environment_map object - buildpsec needs to resolve whether to do any validations
            { name : "APPLICATION", value : var.application },
            { name : "ENVIRONMENT", value : "#{variables.ENVIRONMENT}" },
            # { name : "DNS_ACCOUNT_ID", value : local.base_env_config[stage.value.name].dns_account }, #TODO - DNS account ID is per environment, so we need to pass in all the environment config so that it can be figured out at runtime
          ])
        }
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

  tags = local.tags
}
