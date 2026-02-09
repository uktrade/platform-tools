resource "aws_codebuild_project" "custom_pre_deploy" {
  for_each       = toset(local.has_custom_pre_deploy ? [""] : [])
  name           = "${var.application}-${var.codebase}-custom-pre-deploy"
  description    = "Custom pre-deploy step for ${var.application} ${var.codebase}"
  build_timeout  = 10
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
      group_name  = aws_cloudwatch_log_group.custom_pre_deploy[each.key].name
      stream_name = aws_cloudwatch_log_stream.custom_pre_deploy[each.key].name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = file("${path.module}/buildspec-custom-pre-deploy.yml")
  }

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "custom_pre_deploy" {
  # checkov:skip=CKV_AWS_338:Retains logs for 3 months instead of 1 year
  # checkov:skip=CKV_AWS_158:Log groups encrypted using default encryption key instead of KMS CMK
  for_each          = toset(local.has_custom_pre_deploy ? [""] : [])
  name              = "codebuild/${var.application}-${var.codebase}-custom-pre-deploy/log-group"
  retention_in_days = 90
}

resource "aws_cloudwatch_log_stream" "custom_pre_deploy" {
  for_each       = toset(local.has_custom_pre_deploy ? [""] : [])
  name           = "codebuild/${var.application}-${var.codebase}-custom-pre-deploy/log-stream"
  log_group_name = aws_cloudwatch_log_group.custom_pre_deploy[""].name
}

# POST BUILD

resource "aws_codebuild_project" "custom_post_deploy" {
  for_each       = toset(local.has_custom_post_deploy ? [""] : [])
  name           = "${var.application}-${var.codebase}-custom-post-deploy"
  description    = "Custom post-deploy step for ${var.application} ${var.codebase}"
  build_timeout  = 10
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
      group_name  = aws_cloudwatch_log_group.custom_post_deploy[each.key].name
      stream_name = aws_cloudwatch_log_stream.custom_post_deploy[each.key].name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = file("${path.module}/buildspec-custom-post-deploy.yml")
  }

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "custom_post_deploy" {
  # checkov:skip=CKV_AWS_338:Retains logs for 3 months instead of 1 year
  # checkov:skip=CKV_AWS_158:Log groups encrypted using default encryption key instead of KMS CMK
  for_each          = toset(local.has_custom_post_deploy ? [""] : [])
  name              = "codebuild/${var.application}-${var.codebase}-custom-post-deploy/log-group"
  retention_in_days = 90
}

resource "aws_cloudwatch_log_stream" "custom_post_deploy" {
  for_each       = toset(local.has_custom_post_deploy ? [""] : [])
  name           = "codebuild/${var.application}-${var.codebase}-custom-post-deploy/log-stream"
  log_group_name = aws_cloudwatch_log_group.custom_post_deploy[""].name
}
