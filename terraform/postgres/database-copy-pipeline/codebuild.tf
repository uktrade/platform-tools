# Logs and KMS key
resource "aws_kms_key" "codebuild_kms_key" {
  description         = "KMS Key for ${local.pipeline_name} CodeBuild encryption"
  enable_key_rotation = true

  policy = jsonencode({
    Id = "key-default-1"
    Statement = [
      {
        "Sid" : "Enable IAM User Permissions",
        "Effect" : "Allow",
        "Principal" : {
          "AWS" : "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        },
        "Action" : "kms:*",
        "Resource" : "*"
      }
    ]
    Version = "2012-10-17"
  })

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "database_pipeline_codebuild" {
  # checkov:skip=CKV_AWS_338:Retains logs for 3 months instead of 1 year
  # checkov:skip=CKV_AWS_158:Log groups encrypted using default encryption key instead of KMS CMK
  name              = "codebuild/${local.pipeline_name}/log-group"
  retention_in_days = 90
}

resource "aws_cloudwatch_log_stream" "database_pipeline_codebuild" {
  name           = "codebuild/${local.pipeline_name}/log-stream"
  log_group_name = aws_cloudwatch_log_group.database_pipeline_codebuild.name
}

# Build
resource "aws_codebuild_project" "database_pipeline_build" {
  name           = "${local.pipeline_name}-build"
  description    = "Install the build tools for ${local.pipeline_name}"
  build_timeout  = 5
  service_role   = aws_iam_role.database_pipeline_codebuild.arn
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
      group_name  = aws_cloudwatch_log_group.database_pipeline_codebuild.name
      stream_name = aws_cloudwatch_log_stream.database_pipeline_codebuild.name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = file("${path.module}/buildspec-install-build-tools.yml")
  }

  tags = local.tags
}

# Dump
resource "aws_codebuild_project" "database_pipeline_dump" {
  name           = "${local.pipeline_name}-dump"
  description    = "Dump the ${var.database_name} database from ${var.task.from}"
  build_timeout  = 60
  service_role   = aws_iam_role.database_pipeline_codebuild.arn
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
      group_name  = aws_cloudwatch_log_group.database_pipeline_codebuild.name
      stream_name = aws_cloudwatch_log_stream.database_pipeline_codebuild.name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = file("${path.module}/buildspec-dump.yml")
  }

  tags = local.tags
}

# Load
resource "aws_codebuild_project" "database_pipeline_load" {
  name           = "${local.pipeline_name}-load"
  description    = "Load the ${var.database_name} database to ${var.task.to}"
  build_timeout  = 60
  service_role   = aws_iam_role.database_pipeline_codebuild.arn
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
      group_name  = aws_cloudwatch_log_group.database_pipeline_codebuild.name
      stream_name = aws_cloudwatch_log_stream.database_pipeline_codebuild.name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = file("${path.module}/buildspec-load.yml")
  }

  tags = local.tags
}
