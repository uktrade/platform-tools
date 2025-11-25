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

resource "aws_cloudwatch_log_subscription_filter" "codebase_image_build" {
  for_each        = toset(var.requires_image_build ? [""] : [])
  name            = aws_cloudwatch_log_group.codebase_image_build[""].name
  role_arn        = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"
  log_group_name  = aws_cloudwatch_log_group.codebase_image_build[""].name
  filter_pattern  = ""
  destination_arn = local.central_log_group_destination
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

resource "aws_codebuild_project" "codebase_install_tools" {
  for_each       = toset(local.platform_deployment_enabled ? [""] : [])
  name           = "${var.application}-${var.codebase}-codebase-install-tools"
  description    = "Installs shared build tools for reuse across stages"
  build_timeout  = 5
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
      name  = "PLATFORM_HELPER_VERSION"
      value = var.platform_tools_version
    }

  }

  logs_config {
    cloudwatch_logs {
      group_name  = aws_cloudwatch_log_group.codebase_install_tools[""].name
      stream_name = aws_cloudwatch_log_stream.codebase_install_tools[""].name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = file("${path.module}/buildspec-install-tools.yml")
  }

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "codebase_install_tools" {
  # checkov:skip=CKV_AWS_338:Retains logs for 3 months instead of 1 year
  # checkov:skip=CKV_AWS_158:Log groups encrypted using default encryption key instead of KMS CMK
  for_each          = toset(local.platform_deployment_enabled ? [""] : [])
  name              = "codebuild/${var.application}-${var.codebase}-codebase-install-tools/log-group"
  retention_in_days = 90
}

resource "aws_cloudwatch_log_stream" "codebase_install_tools" {
  for_each       = toset(local.platform_deployment_enabled ? [""] : [])
  name           = "codebuild/${var.application}-${var.codebase}-codebase-install-tools/log-stream"
  log_group_name = aws_cloudwatch_log_group.codebase_install_tools[""].name
}

resource "aws_cloudwatch_log_subscription_filter" "codebase_install_tools" {
  for_each        = toset(local.platform_deployment_enabled ? [""] : [])
  name            = aws_cloudwatch_log_group.codebase_install_tools[""].name
  role_arn        = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"
  log_group_name  = aws_cloudwatch_log_group.codebase_install_tools[""].name
  filter_pattern  = ""
  destination_arn = local.central_log_group_destination
}

resource "aws_codebuild_project" "codebase_service_terraform" {
  for_each       = toset(local.platform_deployment_enabled ? [""] : [])
  name           = "${var.application}-${var.codebase}-codebase-service-terraform"
  description    = "Apply Terraform infrastructure for services"
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

  }

  logs_config {
    cloudwatch_logs {
      group_name  = aws_cloudwatch_log_group.codebase_service_terraform[""].name
      stream_name = aws_cloudwatch_log_stream.codebase_service_terraform[""].name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = file("${path.module}/buildspec-service-terraform.yml")
  }

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "codebase_service_terraform" {
  # checkov:skip=CKV_AWS_338:Retains logs for 3 months instead of 1 year
  # checkov:skip=CKV_AWS_158:Log groups encrypted using default encryption key instead of KMS CMK
  for_each          = toset(local.platform_deployment_enabled ? [""] : [])
  name              = "codebuild/${var.application}-${var.codebase}-codebase-service-terraform/log-group"
  retention_in_days = 90
}

resource "aws_cloudwatch_log_stream" "codebase_service_terraform" {
  for_each       = toset(local.platform_deployment_enabled ? [""] : [])
  name           = "codebuild/${var.application}-${var.codebase}-codebase-service-terraform/log-stream"
  log_group_name = aws_cloudwatch_log_group.codebase_service_terraform[""].name
}

resource "aws_cloudwatch_log_subscription_filter" "codebase_service_terraform" {
  for_each        = toset(local.platform_deployment_enabled ? [""] : [])
  name            = aws_cloudwatch_log_group.codebase_service_terraform[""].name
  role_arn        = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"
  log_group_name  = aws_cloudwatch_log_group.codebase_service_terraform[""].name
  filter_pattern  = ""
  destination_arn = local.central_log_group_destination
}

resource "aws_codebuild_project" "codebase_traffic_switch" {
  for_each       = toset(local.traffic_switch_enabled ? [""] : [])
  name           = "${var.application}-${var.codebase}-codebase-traffic-switch"
  description    = "Perform ALB traffic switch per environment"
  build_timeout  = 30
  service_role   = aws_iam_role.traffic_switch[""].arn
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

  }

  logs_config {
    cloudwatch_logs {
      group_name  = aws_cloudwatch_log_group.codebase_traffic_switch[""].name
      stream_name = aws_cloudwatch_log_stream.codebase_traffic_switch[""].name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = file("${path.module}/buildspec-traffic-switch.yml")
  }

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "codebase_traffic_switch" {
  # checkov:skip=CKV_AWS_338:Retains logs for 3 months instead of 1 year
  # checkov:skip=CKV_AWS_158:Log groups encrypted using default encryption key instead of KMS CMK
  for_each          = toset(local.traffic_switch_enabled ? [""] : [])
  name              = "codebuild/${var.application}-${var.codebase}-codebase-traffic-switch/log-group"
  retention_in_days = 90
}

resource "aws_cloudwatch_log_stream" "codebase_traffic_switch" {
  for_each       = toset(local.traffic_switch_enabled ? [""] : [])
  name           = "codebuild/${var.application}-${var.codebase}-codebase-traffic-switch/log-stream"
  log_group_name = aws_cloudwatch_log_group.codebase_traffic_switch[""].name
}

resource "aws_cloudwatch_log_subscription_filter" "codebase_traffic_switch" {
  for_each        = toset(local.traffic_switch_enabled ? [""] : [])
  name            = aws_cloudwatch_log_group.codebase_traffic_switch[""].name
  role_arn        = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"
  log_group_name  = aws_cloudwatch_log_group.codebase_traffic_switch[""].name
  filter_pattern  = ""
  destination_arn = local.central_log_group_destination
}

resource "aws_codebuild_project" "invalidate_cache" {
  for_each       = toset(local.cache_invalidation_enabled ? [""] : [])
  name           = "${var.application}-${var.codebase}-invalidate-cache"
  description    = "Invalidate the CDN cached paths"
  build_timeout  = 10
  service_role   = aws_iam_role.invalidate_cache[each.key].arn
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
  }

  logs_config {
    cloudwatch_logs {
      group_name  = aws_cloudwatch_log_group.invalidate_cache[each.key].name
      stream_name = aws_cloudwatch_log_stream.invalidate_cache[each.key].name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = file("${path.module}/buildspec-invalidate-cache.yml")
  }

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "invalidate_cache" {
  # checkov:skip=CKV_AWS_338:Retains logs for 3 months instead of 1 year
  # checkov:skip=CKV_AWS_158:Log groups encrypted using default encryption key instead of KMS CMK
  for_each          = toset(local.cache_invalidation_enabled ? [""] : [])
  name              = "codebuild/${var.application}-${var.codebase}-invalidate-cache/log-group"
  retention_in_days = 90
}

resource "aws_cloudwatch_log_stream" "invalidate_cache" {
  for_each       = toset(local.cache_invalidation_enabled ? [""] : [])
  name           = "codebuild/${var.application}-${var.codebase}-invalidate-cache/log-stream"
  log_group_name = aws_cloudwatch_log_group.invalidate_cache[""].name
}

resource "aws_cloudwatch_log_subscription_filter" "invalidate_cache" {
  for_each        = toset(local.cache_invalidation_enabled ? [""] : [])
  name            = aws_cloudwatch_log_group.invalidate_cache[""].name
  role_arn        = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"
  log_group_name  = aws_cloudwatch_log_group.invalidate_cache[""].name
  filter_pattern  = ""
  destination_arn = local.central_log_group_destination
}

resource "aws_codebuild_project" "codebase_deploy" {
  for_each       = toset(local.copilot_deployment_enabled ? [""] : [])
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
      group_name  = aws_cloudwatch_log_group.codebase_deploy[""].name
      stream_name = aws_cloudwatch_log_stream.codebase_deploy[""].name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = file("${path.module}/buildspec-deploy-copilot.yml")
  }

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "codebase_deploy" {
  # checkov:skip=CKV_AWS_338:Retains logs for 3 months instead of 1 year
  # checkov:skip=CKV_AWS_158:Log groups encrypted using default encryption key instead of KMS CMK
  for_each          = toset(local.copilot_deployment_enabled ? [""] : [])
  name              = "codebuild/${var.application}-${var.codebase}-codebase-deploy/log-group"
  retention_in_days = 90
}

resource "aws_cloudwatch_log_stream" "codebase_deploy" {
  for_each       = toset(local.copilot_deployment_enabled ? [""] : [])
  name           = "codebuild/${var.application}-${var.codebase}-codebase-deploy/log-stream"
  log_group_name = aws_cloudwatch_log_group.codebase_deploy[""].name
}

resource "aws_cloudwatch_log_subscription_filter" "codebase_deploy" {
  for_each        = toset(local.copilot_deployment_enabled ? [""] : [])
  name            = aws_cloudwatch_log_group.codebase_deploy[""].name
  role_arn        = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"
  log_group_name  = aws_cloudwatch_log_group.codebase_deploy[""].name
  filter_pattern  = ""
  destination_arn = local.central_log_group_destination
}

resource "aws_codebuild_project" "codebase_deploy_platform" {
  for_each       = toset(local.platform_deployment_enabled ? [""] : [])
  name           = "${var.application}-${var.codebase}-codebase-deploy-platform"
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

  }

  logs_config {
    cloudwatch_logs {
      group_name  = aws_cloudwatch_log_group.codebase_deploy_platform[""].name
      stream_name = aws_cloudwatch_log_stream.codebase_deploy_platform[""].name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = file("${path.module}/buildspec-deploy-platform.yml")
  }

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "codebase_deploy_platform" {
  # checkov:skip=CKV_AWS_338:Retains logs for 3 months instead of 1 year
  # checkov:skip=CKV_AWS_158:Log groups encrypted using default encryption key instead of KMS CMK
  for_each          = toset(local.platform_deployment_enabled ? [""] : [])
  name              = "codebuild/${var.application}-${var.codebase}-codebase-deploy-platform/log-group"
  retention_in_days = 90
}

resource "aws_cloudwatch_log_stream" "codebase_deploy_platform" {
  for_each       = toset(local.platform_deployment_enabled ? [""] : [])
  name           = "codebuild/${var.application}-${var.codebase}-codebase-deploy-platform/log-stream"
  log_group_name = aws_cloudwatch_log_group.codebase_deploy_platform[""].name
}

resource "aws_cloudwatch_log_subscription_filter" "codebase_deploy_platform" {
  for_each        = toset(local.platform_deployment_enabled ? [""] : [])
  name            = aws_cloudwatch_log_group.codebase_deploy_platform[""].name
  role_arn        = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"
  log_group_name  = aws_cloudwatch_log_group.codebase_deploy_platform[""].name
  filter_pattern  = ""
  destination_arn = local.central_log_group_destination
}

resource "aws_codebuild_project" "codebase_service_terraform_plan" {
  for_each       = toset(local.platform_deployment_enabled ? [""] : [])
  name           = "${var.application}-${var.codebase}-codebase-service-terraform-plan"
  description    = "Plan service terraform changes for approval"
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

  }

  logs_config {
    cloudwatch_logs {
      group_name  = aws_cloudwatch_log_group.codebase_service_terraform_plan[""].name
      stream_name = aws_cloudwatch_log_stream.codebase_service_terraform_plan[""].name
    }
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = file("${path.module}/buildspec-service-terraform-plan.yml")
  }

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "codebase_service_terraform_plan" {
  # checkov:skip=CKV_AWS_338:Retains logs for 3 months instead of 1 year
  # checkov:skip=CKV_AWS_158:Log groups encrypted using default encryption key instead of KMS CMK
  for_each          = toset(local.platform_deployment_enabled ? [""] : [])
  name              = "codebuild/${var.application}-${var.codebase}-codebase-service-terraform-plan/log-group"
  retention_in_days = 90
}

resource "aws_cloudwatch_log_stream" "codebase_service_terraform_plan" {
  for_each       = toset(local.platform_deployment_enabled ? [""] : [])
  name           = "codebuild/${var.application}-${var.codebase}-codebase-service-terraform-plan/log-stream"
  log_group_name = aws_cloudwatch_log_group.codebase_service_terraform_plan[""].name
}

resource "aws_cloudwatch_log_subscription_filter" "codebase_service_terraform_plan" {
  for_each        = toset(local.platform_deployment_enabled ? [""] : [])
  name            = aws_cloudwatch_log_group.codebase_service_terraform_plan[""].name
  role_arn        = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/CWLtoSubscriptionFilterRole"
  log_group_name  = aws_cloudwatch_log_group.codebase_service_terraform_plan[""].name
  filter_pattern  = ""
  destination_arn = local.central_log_group_destination
}

# These moved blocks are to prevent resources being recreated
moved {
  from = aws_codebuild_project.codebase_deploy
  to   = aws_codebuild_project.codebase_deploy[""]
}

moved {
  from = aws_cloudwatch_log_group.codebase_deploy
  to   = aws_cloudwatch_log_group.codebase_deploy[""]
}

moved {
  from = aws_cloudwatch_log_stream.codebase_deploy
  to   = aws_cloudwatch_log_stream.codebase_deploy[""]
}
