resource "aws_codebuild_project" "custom_pre_build" {
  for_each       = toset(local.has_custom_pre_build ? [""] : [])
  name           = "${var.application}-${var.codebase}-custom-pre-build"
  description    = "Custom pre-build step for ${var.application} ${var.codebase}"
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

    # environment_variable {
    #   name  = "ENV_CONFIG"
    #   value = jsonencode(local.base_env_config)
    # }
  }

  logs_config {
    cloudwatch_logs {
      group_name  = aws_cloudwatch_log_group.custom_pre_build[each.key].name
      stream_name = aws_cloudwatch_log_stream.custom_pre_build[each.key].name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = file("${path.module}/buildspec-custom-pre-build.yml")
  }

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "custom_pre_build" {
  # checkov:skip=CKV_AWS_338:Retains logs for 3 months instead of 1 year
  # checkov:skip=CKV_AWS_158:Log groups encrypted using default encryption key instead of KMS CMK
  for_each          = toset(local.has_custom_pre_build ? [""] : [])
  name              = "codebuild/${var.application}-${var.codebase}-custom-pre-build/log-group"
  retention_in_days = 90
}

resource "aws_cloudwatch_log_stream" "custom_pre_build" {
  for_each       = toset(local.has_custom_pre_build ? [""] : [])
  name           = "codebuild/${var.application}-${var.codebase}-custom-pre-build/log-stream"
  log_group_name = aws_cloudwatch_log_group.custom_pre_build[""].name
}

# POST BUILD

resource "aws_codebuild_project" "custom_post_build" {
  for_each       = toset(local.has_custom_post_build ? [""] : [])
  name           = "${var.application}-${var.codebase}-custom-post-build"
  description    = "Custom post-build step for ${var.application} ${var.codebase}"
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

    # environment_variable {
    #   name  = "ENV_CONFIG"
    #   value = jsonencode(local.base_env_config)
    # }
  }

  logs_config {
    cloudwatch_logs {
      group_name  = aws_cloudwatch_log_group.custom_post_build[each.key].name
      stream_name = aws_cloudwatch_log_stream.custom_post_build[each.key].name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = file("${path.module}/buildspec-custom-post-build.yml")
  }

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "custom_post_build" {
  # checkov:skip=CKV_AWS_338:Retains logs for 3 months instead of 1 year
  # checkov:skip=CKV_AWS_158:Log groups encrypted using default encryption key instead of KMS CMK
  for_each          = toset(local.has_custom_post_build ? [""] : [])
  name              = "codebuild/${var.application}-${var.codebase}-custom-post-build/log-group"
  retention_in_days = 90
}

resource "aws_cloudwatch_log_stream" "custom_post_build" {
  for_each       = toset(local.has_custom_post_build ? [""] : [])
  name           = "codebuild/${var.application}-${var.codebase}-custom-post-build/log-stream"
  log_group_name = aws_cloudwatch_log_group.custom_post_build[""].name
}
