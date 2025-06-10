resource "aws_codebuild_project" "environment_pipeline_build" {
  name           = "${var.application}-${var.pipeline_name}-environment-pipeline-build"
  description    = "Provisions the ${var.application} application's extensions."
  build_timeout  = 5
  service_role   = aws_iam_role.environment_pipeline_codebuild.arn
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
      group_name  = aws_cloudwatch_log_group.environment_pipeline_codebuild.name
      stream_name = aws_cloudwatch_log_stream.environment_pipeline_codebuild.name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = file("${path.module}/buildspec-install-build-tools.yml")
  }

  tags = local.tags
}

resource "aws_kms_key" "codebuild_kms_key" {
  description         = "KMS Key for ${var.application}-${var.pipeline_name} CodeBuild encryption"
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

resource "aws_cloudwatch_log_group" "environment_pipeline_codebuild" {
  # checkov:skip=CKV_AWS_338:Retains logs for 3 months instead of 1 year
  # checkov:skip=CKV_AWS_158: To be reworked
  name              = "codebuild/${var.application}-${var.pipeline_name}-environment-terraform/log-group"
  retention_in_days = 90
  # kms_key_id        = aws_kms_key.codebuild_kms_key.arn
}

resource "aws_cloudwatch_log_stream" "environment_pipeline_codebuild" {
  name           = "codebuild/${var.application}-${var.pipeline_name}-environment-terraform/log-stream"
  log_group_name = aws_cloudwatch_log_group.environment_pipeline_codebuild.name
}

# Terraform plan
resource "aws_codebuild_project" "environment_pipeline_plan" {
  name           = "${var.application}-${var.pipeline_name}-environment-pipeline-plan"
  description    = "Provisions the ${var.application} application's extensions."
  build_timeout  = 5
  service_role   = aws_iam_role.environment_pipeline_codebuild.arn
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
      group_name  = aws_cloudwatch_log_group.environment_pipeline_codebuild.name
      stream_name = aws_cloudwatch_log_stream.environment_pipeline_codebuild.name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = file("${path.module}/buildspec-plan.yml")
  }

  tags = local.tags
}

# Terraform apply
resource "aws_codebuild_project" "environment_pipeline_apply" {
  name           = "${var.application}-${var.pipeline_name}-environment-pipeline-apply"
  description    = "Provisions the ${var.application} application's extensions."
  build_timeout  = 120
  service_role   = aws_iam_role.environment_pipeline_codebuild.arn
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
      group_name  = aws_cloudwatch_log_group.environment_pipeline_codebuild.name
      stream_name = aws_cloudwatch_log_stream.environment_pipeline_codebuild.name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = file("${path.module}/buildspec-apply.yml")
  }

  tags = local.tags
}
