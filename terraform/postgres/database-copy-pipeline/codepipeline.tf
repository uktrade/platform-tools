data "aws_iam_account_alias" "current" {}

data "external" "codestar_connections" {
  program = ["bash", "-c", <<-EOT
    aws codeconnections list-connections --provider-type GitHub --query "Connections[?ConnectionName=='${data.aws_iam_account_alias.current.account_alias}' && ConnectionStatus=='AVAILABLE'] | [0]" --output json
  EOT
  ]
}

resource "aws_codepipeline" "database_copy_pipeline" {
  name           = local.pipeline_name
  role_arn       = aws_iam_role.database_pipeline_codepipeline.arn
  depends_on     = [aws_iam_role_policy.artifact_store_access_for_database_pipeline]
  pipeline_type  = "V2"
  execution_mode = "QUEUED"
  tags           = local.tags

  variable {
    name          = "PLATFORM_HELPER_VERSION_OVERRIDE"
    default_value = "NONE"
    description   = "Override the platform-helper default version specified in platform-config"
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
      output_artifacts = ["project_deployment_source"]

      configuration = {
        ConnectionArn    = data.external.codestar_connections.result["ConnectionArn"]
        FullRepositoryId = "uktrade/${var.application}-deploy"
        BranchName       = "main"
        DetectChanges    = false
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
        ProjectName   = "${local.pipeline_name}-build"
        PrimarySource = "project_deployment_source"
        EnvironmentVariables : jsonencode([
          { name : "PIPELINE_NAME", value : local.pipeline_name },
          { name : "DATABASE_NAME", value : var.database_name },
          { name : "FROM_ENVIRONMENT", value : var.task.from },
          { name : "TO_ENVIRONMENT", value : var.task.to },
          { name : "PLATFORM_HELPER_VERSION_OVERRIDE", value : "#{variables.PLATFORM_HELPER_VERSION_OVERRIDE}" },
        ])
      }
    }
  }

  stage {
    name = "Database-Dump-${var.task.from}"

    action {
      name             = "Dump"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      input_artifacts  = ["build_output"]
      output_artifacts = []
      version          = "1"

      configuration = {
        ProjectName   = "${local.pipeline_name}-dump"
        PrimarySource = "build_output"
        EnvironmentVariables : jsonencode([
          { name : "APPLICATION", value : var.application },
          { name : "DATABASE_NAME", value : var.database_name },
          { name : "FROM_ENVIRONMENT", value : var.task.from },
          { name : "TO_ENVIRONMENT", value : var.task.to },
          { name : "DUMP_ROLE_ARN", value : local.dump_role_arn },
          { name : "SLACK_REF", value : "#{slack.SLACK_REF}" }
        ])
      }
    }
  }

  stage {
    name = "Database-Load-${var.task.to}"

    action {
      name             = "Load"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      input_artifacts  = ["build_output"]
      output_artifacts = []
      version          = "1"

      configuration = {
        ProjectName   = "${local.pipeline_name}-load"
        PrimarySource = "build_output"
        EnvironmentVariables : jsonencode([
          { name : "APPLICATION", value : var.application },
          { name : "DATABASE_NAME", value : var.database_name },
          { name : "FROM_ENVIRONMENT", value : var.task.from },
          { name : "TO_ENVIRONMENT", value : var.task.to },
          { name : "LOAD_ROLE_ARN", value : local.load_role_arn },
          { name : "SLACK_REF", value : "#{slack.SLACK_REF}" }
        ])
      }
    }
  }
}
