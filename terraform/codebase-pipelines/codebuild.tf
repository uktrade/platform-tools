data "aws_ssm_parameter" "connection_name" {
  name = "/codestarconnection/name"
}

data "external" "codestar_connections" {
  program = ["bash", "-c", <<-EOT
    aws codeconnections list-connections --provider-type GitHub --query "Connections[?ConnectionName=='${data.aws_ssm_parameter.connection_name.value}' && ConnectionStatus=='AVAILABLE'] | [0]" --output json
  EOT
  ]
}

resource "aws_codebuild_project" "codebase_image_build" {
  for_each      = toset(var.requires_image_build ? [""] : [])
  name          = "${var.application}-${var.codebase}-codebase-image-build"
  description   = "Publish images on push to ${var.repository}"
  build_timeout = 30
  service_role  = aws_iam_role.codebase_image_build[""].arn
  badge_enabled = true

  artifacts {
    type = "NO_ARTIFACTS"
  }

  cache {
    type  = "LOCAL"
    modes = ["LOCAL_DOCKER_LAYER_CACHE"]
  }

  environment {
    compute_type = "BUILD_GENERAL1_SMALL"
    image        = "public.ecr.aws/uktrade/ci-image-builder:tag-latest"
    type         = "LINUX_CONTAINER"

    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = data.aws_caller_identity.current.account_id
    }

    environment_variable {
      name  = "ECR_REPOSITORY"
      value = local.ecr_name
    }

    environment_variable {
      name  = "CODESTAR_CONNECTION_ARN"
      value = data.external.codestar_connections.result["ConnectionArn"]
    }

    environment_variable {
      name  = "SLACK_CHANNEL_ID"
      value = var.slack_channel
      type  = "PARAMETER_STORE"
    }

    dynamic "environment_variable" {
      for_each = var.additional_ecr_repository != null ? [1] : []
      content {
        name  = "ADDITIONAL_ECR_REPOSITORY"
        value = var.additional_ecr_repository
      }
    }
  }

  logs_config {
    cloudwatch_logs {
      group_name  = aws_cloudwatch_log_group.codebase_image_build[""].name
      stream_name = aws_cloudwatch_log_stream.codebase_image_build[""].name
    }
  }

  source {
    type            = "GITHUB"
    buildspec       = file("${path.module}/buildspec-images.yml")
    location        = "https://github.com/${var.repository}.git"
    git_clone_depth = 0
    git_submodules_config {
      fetch_submodules = false
    }
  }

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "codebase_image_build" {
  # checkov:skip=CKV_AWS_338:Retains logs for 3 months instead of 1 year
  # checkov:skip=CKV_AWS_158:Log groups encrypted using default encryption key instead of KMS CMK
  for_each          = toset(var.requires_image_build ? [""] : [])
  name              = "codebuild/${var.application}-${var.codebase}-codebase-image-build/log-group"
  retention_in_days = 90
}

resource "aws_cloudwatch_log_stream" "codebase_image_build" {
  for_each       = toset(var.requires_image_build ? [""] : [])
  name           = "codebuild/${var.application}-${var.codebase}-codebase-image-build/log-stream"
  log_group_name = aws_cloudwatch_log_group.codebase_image_build[""].name
}

resource "aws_codebuild_webhook" "codebuild_webhook" {
  for_each     = toset(var.requires_image_build ? [""] : [])
  project_name = aws_codebuild_project.codebase_image_build[""].name
  build_type   = "BUILD"

  dynamic "filter_group" {
    for_each = local.pipeline_branches
    content {
      filter {
        type    = "EVENT"
        pattern = "PUSH"
      }

      filter {
        type    = "HEAD_REF"
        pattern = "^refs/heads/${filter_group.value}$"
      }
    }
  }

  dynamic "filter_group" {
    for_each = local.tagged_pipeline ? [1] : []
    content {
      filter {
        type    = "EVENT"
        pattern = "PUSH"
      }

      filter {
        type    = "HEAD_REF"
        pattern = "^refs/tags/.*"
      }
    }
  }
}


resource "aws_codebuild_project" "invalidate_cache" {
  name           = "${var.application}-${var.codebase}-invalidate-cache"
  description    = "Invalidate the CDN cached paths"
  build_timeout  = 30
  service_role   = aws_iam_role.codebase_deploy.arn
  encryption_key = aws_kms_key.artifact_store_kms_key.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  cache {
    type     = "S3"
    location = aws_s3_bucket.artifact_store.bucket
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
  }

  logs_config {
    cloudwatch_logs {
      group_name  = aws_cloudwatch_log_group.codebase_deploy.name
      stream_name = aws_cloudwatch_log_stream.codebase_deploy.name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = file("${path.module}/buildspec-invalidate-cache.yml")
  }

  tags = local.tags
}


resource "aws_codebuild_project" "codebase_deploy" {
  name           = "${var.application}-${var.codebase}-codebase-deploy"
  description    = "Deploy specified image tag to specified environment"
  build_timeout  = 30
  service_role   = aws_iam_role.codebase_deploy.arn
  encryption_key = aws_kms_key.artifact_store_kms_key.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  cache {
    type     = "S3"
    location = aws_s3_bucket.artifact_store.bucket
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"

    environment_variable {
      name  = "ENV_CONFIG"
      value = jsonencode(local.base_env_config)
    }

    environment_variable {
      name  = "CODESTAR_CONNECTION_ARN"
      value = data.external.codestar_connections.result["ConnectionArn"]
    }

    environment_variable {
      name  = "PLATFORM_HELPER_VERSION"
      value = var.platform_tools_version
    }
  }

  logs_config {
    cloudwatch_logs {
      group_name  = aws_cloudwatch_log_group.codebase_deploy.name
      stream_name = aws_cloudwatch_log_stream.codebase_deploy.name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = file("${path.module}/buildspec-deploy.yml")
  }

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "codebase_deploy" {
  # checkov:skip=CKV_AWS_338:Retains logs for 3 months instead of 1 year
  # checkov:skip=CKV_AWS_158:Log groups encrypted using default encryption key instead of KMS CMK
  name              = "codebuild/${var.application}-${var.codebase}-codebase-deploy/log-group"
  retention_in_days = 90
}

resource "aws_cloudwatch_log_stream" "codebase_deploy" {
  name           = "codebuild/${var.application}-${var.codebase}-codebase-deploy/log-stream"
  log_group_name = aws_cloudwatch_log_group.codebase_deploy.name
}
