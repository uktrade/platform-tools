mock_provider "aws" {}

override_data {
  target = data.external.codestar_connections

  values = {
    result = {
      ConnectionArn = "ConnectionArn"
    }
  }
}
override_data {
  target = data.aws_iam_policy_document.assume_codebuild_role
  values = {
    json = "{\"Sid\": \"AssumeCodebuildRole\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.log_access
  values = {
    json = "{\"Sid\": \"CodeBuildLogs\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.ecr_access_for_codebuild_images
  values = {
    json = "{\"Sid\": \"CodeBuildImageECRAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.codestar_connection_access
  values = {
    json = "{\"Sid\": \"CodeStarConnectionAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.assume_codepipeline_role
  values = {
    json = "{\"Sid\": \"AssumeCodepipelineRole\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.assume_event_bridge_policy
  values = {
    json = "{\"Sid\": \"AssumeEventBridge\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.event_bridge_pipeline_trigger
  values = {
    json = "{\"Sid\": \"EventBridgePipelineTrigger\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.environment_deploy_role_access
  values = {
    json = "{\"Sid\": \"EnvironmentDeployAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.deploy_ssm_access
  values = {
    json = "{\"Sid\": \"SSMAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.ecr_access_for_codebase_pipeline
  values = {
    json = "{\"Sid\": \"PipelineECRAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.env_manager_access
  values = {
    json = "{\"Sid\": \"AssumeEnvManagerAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.ecr_policy
  values = {
    json = "{\"Sid\": \"ECRPolicy\"}"
  }
}

variables {
  env_config = {
    "*" = {
      accounts = {
        deploy = {
          name = "sandbox"
          id   = "000123456789"
        }
        dns = {
          name = "dev"
          id   = "111123456789"
        }
      }
    },
    "dev"     = null,
    "staging" = null,
    "prod" = {
      accounts = {
        deploy = {
          name = "prod"
          id   = "123456789000"
        }
        dns = {
          name = "live"
          id   = "222223456789"
        }
      }
    }
  }
  application = "my-app"
  codebase    = "my-codebase"
  repository  = "my-repository"
  services = [
    {
      "run_group_1" : [
        "service-1"
      ]
    },
    {
      "run_group_2" : [
        "service-2"
      ]
    }
  ]
  cache_invalidation = {
    domains = {
      "service-1.env-1.my-app.uktrade.digital" : {
        paths       = ["a", "b"]
        environment = "env-1"
      },
      "service-2.env-1.my-app.uktrade.digital" : {
        paths       = ["c", "d"]
        environment = "env-1"
      },
      "service-2.env-2.my-app.uktrade.digital" : {
        paths       = ["e", "f"]
        environment = "env-2"
      }
    }
  }
  pipelines = [
    {
      name   = "main",
      branch = "main",
      environments = [
        { name = "dev" }
      ]
    },
    {
      name = "tagged",
      tag  = true,
      environments = [
        { name = "staging" },
        { name = "prod", requires_approval = true }
      ]
    }
  ]
  expected_tags = {
    application         = "my-app"
    copilot-application = "my-app"
    managed-by          = "DBT Platform - Terraform"
  }
  expected_ecr_tags = {
    copilot-pipeline    = "my-codebase"
    copilot-application = "my-app"
  }

  slack_channel = "/fake/slack/channel"
}

run "test_locals" {
  command = plan

  assert {
    condition     = length(local.base_env_config) == 3
    error_message = "Should be:"
  }
  assert {
    condition     = local.base_env_config["dev"].account == "000123456789"
    error_message = "Should be:"
  }
  assert {
    condition     = local.base_env_config["dev"].dns_account == "111123456789"
    error_message = "Should be:"
  }
  assert {
    condition     = local.base_env_config["staging"].dns_account == "111123456789"
    error_message = "Should be:"
  }
  assert {
    condition     = local.base_env_config["prod"].dns_account == "222223456789"
    error_message = "Should be:"
  }
  assert {
    condition     = local.dns_account_ids[0] == "111123456789"
    error_message = "Should be:"
  }
  assert {
    condition     = local.dns_account_ids[1] == "222223456789"
    error_message = "Should be:"
  }
  assert {
    condition     = contains(local.cache_invalidation_map.env-1["service-1.env-1.my-app.uktrade.digital"], "a")
    error_message = "Should be:"
  }
  assert {
    condition     = contains(local.cache_invalidation_map.env-1["service-1.env-1.my-app.uktrade.digital"], "b")
    error_message = "Should be:"
  }
  assert {
    condition     = contains(local.cache_invalidation_map.env-1["service-2.env-1.my-app.uktrade.digital"], "c")
    error_message = "Should be:"
  }
  assert {
    condition     = contains(local.cache_invalidation_map.env-1["service-2.env-1.my-app.uktrade.digital"], "d")
    error_message = "Should be:"
  }
  assert {
    condition     = contains(local.cache_invalidation_map.env-2["service-2.env-2.my-app.uktrade.digital"], "e")
    error_message = "Should be:"
  }
  assert {
    condition     = contains(local.cache_invalidation_map.env-2["service-2.env-2.my-app.uktrade.digital"], "f")
    error_message = "Should be:"
  }
  assert {
    condition     = local.cache_invalidation_enabled == true
    error_message = "Should be:"
  }
}

run "test_ecr" {
  command = plan

  assert {
    condition     = aws_ecr_repository.this.name == "my-app/my-codebase"
    error_message = "Should be: my-app/my-codebase"
  }
  assert {
    condition     = jsonencode(aws_ecr_repository.this.tags) == jsonencode(var.expected_ecr_tags)
    error_message = "Should be: ${jsonencode(var.expected_ecr_tags)}"
  }
  assert {
    condition     = aws_ecr_repository_policy.ecr_policy.repository == "my-app/my-codebase"
    error_message = "Should be: 'my-app/my-codebase'"
  }
  assert {
    condition     = aws_ecr_repository_policy.ecr_policy.policy == "{\"Sid\": \"ECRPolicy\"}"
    error_message = "Should be: {\"Sid\": \"ECRPolicy\"}"
  }
  assert {
    condition     = data.aws_iam_policy_document.ecr_policy.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.ecr_policy.statement[0].actions == toset([
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:CompleteLayerUpload",
      "ecr:GetDownloadUrlForLayer",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = [for el in data.aws_iam_policy_document.ecr_policy.statement[0].principals : el.type][0] == "AWS"
    error_message = "Should be: AWS"
  }
  assert {
    condition     = flatten([for el in data.aws_iam_policy_document.ecr_policy.statement[0].principals : el.identifiers]) == ["arn:aws:iam::000123456789:root", "arn:aws:iam::123456789000:root"]
    error_message = "ECR policy principals incorrect"
  }
}

run "test_artifact_store" {
  command = plan

  assert {
    condition     = aws_s3_bucket.artifact_store.bucket == "my-app-my-codebase-cb-arts"
    error_message = "Should be: my-app-my-codebase-cb-arts"
  }
  assert {
    condition     = aws_kms_alias.artifact_store_kms_alias.name == "alias/my-app-my-codebase-cb-arts-key"
    error_message = "Should be: alias/my-app-my-codebase-cb-arts-key"
  }
  assert {
    condition     = [for el in data.aws_iam_policy_document.artifact_store_bucket_policy.statement[0].condition : el.variable][0] == "aws:SecureTransport"
    error_message = "Should be: aws:SecureTransport"
  }
  assert {
    condition     = data.aws_iam_policy_document.artifact_store_bucket_policy.statement[0].effect == "Deny"
    error_message = "Should be: Deny"
  }
  assert {
    condition     = [for el in data.aws_iam_policy_document.artifact_store_bucket_policy.statement[0].actions : el][0] == "s3:*"
    error_message = "Should be: s3:*"
  }
  assert {
    condition     = [for el in data.aws_iam_policy_document.artifact_store_bucket_policy.statement[1].principals : el.type][0] == "AWS"
    error_message = "Should be: AWS"
  }
  assert {
    condition     = flatten([for el in data.aws_iam_policy_document.artifact_store_bucket_policy.statement[1].principals : el.identifiers]) == ["arn:aws:iam::000123456789:root", "arn:aws:iam::123456789000:root"]
    error_message = "Bucket policy principals incorrect"
  }
  assert {
    condition     = one([for el in data.aws_iam_policy_document.artifact_store_bucket_policy.statement[1].condition : el.test]) == "ArnLike"
    error_message = "Bucket policy condition incorrect"
  }
  assert {
    condition     = one([for el in data.aws_iam_policy_document.artifact_store_bucket_policy.statement[1].condition : el.variable]) == "aws:PrincipalArn"
    error_message = "Bucket policy condition incorrect"
  }
  assert {
    condition     = flatten([for el in data.aws_iam_policy_document.artifact_store_bucket_policy.statement[1].condition : el.values]) == ["arn:aws:iam::000123456789:role/my-app-*-codebase-pipeline-deploy", "arn:aws:iam::123456789000:role/my-app-*-codebase-pipeline-deploy"]
    error_message = "Bucket policy condition incorrect"
  }
  assert {
    condition     = [for el in data.aws_iam_policy_document.artifact_store_bucket_policy.statement[1].actions : el][0] == "s3:*"
    error_message = "Should be: s3:*"
  }
}

run "test_codebuild_images" {
  command = plan

  assert {
    condition     = aws_codebuild_project.codebase_image_build[""].name == "my-app-my-codebase-codebase-image-build"
    error_message = "Should be: my-app-my-codebase-codebase-image-build"
  }
  assert {
    condition     = aws_codebuild_project.codebase_image_build[""].description == "Publish images on push to my-repository"
    error_message = "Should be: 'Publish images on push to my-repository'"
  }
  assert {
    condition     = aws_codebuild_project.codebase_image_build[""].build_timeout == 30
    error_message = "Should be: 30"
  }
  assert {
    condition     = one(aws_codebuild_project.codebase_image_build[""].artifacts).type == "NO_ARTIFACTS"
    error_message = "Should be: 'NO_ARTIFACTS'"
  }
  assert {
    condition     = one(aws_codebuild_project.codebase_image_build[""].cache).type == "LOCAL"
    error_message = "Should be: 'LOCAL'"
  }
  assert {
    condition     = one(aws_codebuild_project.codebase_image_build[""].cache).modes[0] == "LOCAL_DOCKER_LAYER_CACHE"
    error_message = "Should be: 'LOCAL_DOCKER_LAYER_CACHE'"
  }
  assert {
    condition     = one(aws_codebuild_project.codebase_image_build[""].environment).compute_type == "BUILD_GENERAL1_SMALL"
    error_message = "Should be: 'BUILD_GENERAL1_SMALL'"
  }
  assert {
    condition     = one(aws_codebuild_project.codebase_image_build[""].environment).image == "public.ecr.aws/uktrade/ci-image-builder:tag-latest"
    error_message = "Should be: 'public.ecr.aws/uktrade/ci-image-builder:tag-latest'"
  }
  assert {
    condition = one([for var in one(aws_codebuild_project.codebase_image_build[""].environment).environment_variable :
    var.value if var.name == "ECR_REPOSITORY"]) == "my-app/my-codebase"
    error_message = "Should be: 'my-app/my-codebase'"
  }
  assert {
    condition = one([for var in one(aws_codebuild_project.codebase_image_build[""].environment).environment_variable :
    var.value if var.name == "SLACK_CHANNEL_ID"]) == "/fake/slack/channel"
    error_message = "Should be: '/fake/slack/channel'"
  }
  assert {
    condition = aws_codebuild_project.codebase_image_build[""].logs_config[0].cloudwatch_logs[
      0
    ].group_name == "codebuild/my-app-my-codebase-codebase-image-build/log-group"
    error_message = "Should be: 'codebuild/my-app-my-codebase-codebase-image-build/log-group'"
  }
  assert {
    condition = aws_codebuild_project.codebase_image_build[""].logs_config[0].cloudwatch_logs[
      0
    ].stream_name == "codebuild/my-app-my-codebase-codebase-image-build/log-stream"
    error_message = "Should be: 'codebuild/my-app-my-codebase-codebase-image-build/log-stream'"
  }
  assert {
    condition     = one(aws_codebuild_project.codebase_image_build[""].source).type == "GITHUB"
    error_message = "Should be: 'GITHUB'"
  }
  assert {
    condition     = one(aws_codebuild_project.codebase_image_build[""].source).location == "https://github.com/my-repository.git"
    error_message = "Should be: 'https://github.com/my-repository.git'"
  }
  assert {
    condition     = length(regexall(".*/work/cli build.*", aws_codebuild_project.codebase_image_build[""].source[0].buildspec)) > 0
    error_message = "Should contain: '/work/cli build'"
  }
  assert {
    condition     = jsonencode(aws_codebuild_project.codebase_image_build[""].tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }

  # Cloudwatch config:
  assert {
    condition     = aws_cloudwatch_log_group.codebase_image_build[""].name == "codebuild/my-app-my-codebase-codebase-image-build/log-group"
    error_message = "Should be: 'codebuild/my-app-my-codebase-codebase-image-build/log-group'"
  }
  assert {
    condition     = aws_cloudwatch_log_group.codebase_image_build[""].retention_in_days == 90
    error_message = "Should be: 90"
  }
  assert {
    condition     = aws_cloudwatch_log_stream.codebase_image_build[""].name == "codebuild/my-app-my-codebase-codebase-image-build/log-stream"
    error_message = "Should be: 'codebuild/my-app-my-codebase-codebase-image-build/log-stream'"
  }
  assert {
    condition     = aws_cloudwatch_log_stream.codebase_image_build[""].log_group_name == "codebuild/my-app-my-codebase-codebase-image-build/log-group"
    error_message = "Should be: 'codebuild/my-app-my-codebase-codebase-image-build/log-group'"
  }

  # Webhook config:
  assert {
    condition     = aws_codebuild_webhook.codebuild_webhook[""].project_name == "my-app-my-codebase-codebase-image-build"
    error_message = "Should be: 'my-app-my-codebase-codebase-image-build'"
  }
  assert {
    condition     = aws_codebuild_webhook.codebuild_webhook[""].build_type == "BUILD"
    error_message = "Should be: 'BUILD'"
  }

  assert {
    condition     = length(aws_codebuild_webhook.codebuild_webhook[""].filter_group) == 2
    error_message = "Should be: 2"
  }
  assert {
    condition = [
      for el in aws_codebuild_webhook.codebuild_webhook[""].filter_group : true
      if[for filter in el.filter : true if filter.type == "EVENT" && filter.pattern == "PUSH"][0] == true
      ][
      0
    ] == true
    error_message = "Should be: type = 'EVENT' and pattern = 'PUSH'"
  }
}

run "test_codebuild_images_not_required" {
  command = plan

  variables {
    requires_image_build = false
  }

  assert {
    condition     = length(aws_codebuild_project.codebase_image_build) == 0
    error_message = "Should be: 0"
  }
  assert {
    condition     = length(aws_iam_role.codebase_image_build) == 0
    error_message = "Should be: 0"
  }
  assert {
    condition     = length(aws_cloudwatch_log_group.codebase_image_build) == 0
    error_message = "Should be: 0"
  }
  assert {
    condition     = length(aws_cloudwatch_log_stream.codebase_image_build) == 0
    error_message = "Should be: 0"
  }
  assert {
    condition     = length(aws_codebuild_webhook.codebuild_webhook) == 0
    error_message = "Should be: 0"
  }
  assert {
    condition     = aws_cloudwatch_event_rule.ecr_image_publish[0].event_pattern == "{\"detail\":{\"action-type\":[\"PUSH\"],\"image-tag\":[\"latest\"],\"repository-name\":[\"my-app/my-codebase\"],\"result\":[\"SUCCESS\"]},\"detail-type\":[\"ECR Image Action\"],\"source\":[\"aws.ecr\"]}"
    error_message = "Event pattern is incorrect"
  }
  assert {
    condition     = aws_cloudwatch_event_rule.ecr_image_publish[1].event_pattern == "{\"detail\":{\"action-type\":[\"PUSH\"],\"image-tag\":[\"latest\"],\"repository-name\":[\"my-app/my-codebase\"],\"result\":[\"SUCCESS\"]},\"detail-type\":[\"ECR Image Action\"],\"source\":[\"aws.ecr\"]}"
    error_message = "Event pattern is incorrect"
  }
}

run "test_additional_private_ecr_repository" {
  command = plan

  variables {
    additional_ecr_repository = "repository-namespace/repository-name"
  }

  assert {
    condition     = local.is_additional_repo_public == false
    error_message = "Should be: false"
  }
  assert {
    condition = one([for var in one(aws_codebuild_project.codebase_image_build[""].environment).environment_variable :
    var.value if var.name == "ADDITIONAL_ECR_REPOSITORY"]) == "repository-namespace/repository-name"
    error_message = "Should be: repository-namespace/repository-name"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.codebase_pipeline[0].stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "REPOSITORY_URL"]) == "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/repository-namespace/repository-name"
    error_message = "REPOSITORY_URL environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.manual_release_pipeline.stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "REPOSITORY_URL"]) == "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/repository-namespace/repository-name"
    error_message = "REPOSITORY_URL environment variable incorrect"
  }
  assert {
    condition = data.aws_iam_policy_document.ecr_access_for_codebuild_images.statement[1].resources == toset([
      "arn:aws:ecr:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:repository/my-app/my-codebase",
      "arn:aws:ecr:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:repository/repository-namespace/repository-name"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = length(data.aws_iam_policy_document.ecr_access_for_codebuild_images.statement[1].resources) == 2
    error_message = "Unexpected resources"
  }
  assert {
    condition = data.aws_iam_policy_document.ecr_access_for_codebase_pipeline.statement[0].resources == toset([
      "arn:aws:ecr:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:repository/my-app/my-codebase",
      "arn:aws:ecr:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:repository/repository-namespace/repository-name"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = length(data.aws_iam_policy_document.ecr_access_for_codebase_pipeline.statement[0].resources) == 2
    error_message = "Unexpected resources"
  }
}

run "test_additional_ecr_repository_public" {
  command = plan

  variables {
    additional_ecr_repository = "public.ecr.aws/repository-namespace/repository-name"
  }

  assert {
    condition     = local.is_additional_repo_public == true
    error_message = "Should be: true"
  }
  assert {
    condition = one([for var in one(aws_codebuild_project.codebase_image_build[""].environment).environment_variable :
    var.value if var.name == "ADDITIONAL_ECR_REPOSITORY"]) == "public.ecr.aws/repository-namespace/repository-name"
    error_message = "Should be: 'public.ecr.aws/repository-namespace/repository-name'"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.codebase_pipeline[0].stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "REPOSITORY_URL"]) == "public.ecr.aws/repository-namespace/repository-name"
    error_message = "REPOSITORY_URL environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.manual_release_pipeline.stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "REPOSITORY_URL"]) == "public.ecr.aws/repository-namespace/repository-name"
    error_message = "REPOSITORY_URL environment variable incorrect"
  }
  assert {
    condition     = data.aws_iam_policy_document.ecr_access_for_codebuild_images.statement[2].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.ecr_access_for_codebuild_images.statement[2].actions == toset([
      "ecr-public:DescribeImageScanFindings",
      "ecr-public:GetLifecyclePolicyPreview",
      "ecr-public:GetDownloadUrlForLayer",
      "ecr-public:BatchGetImage",
      "ecr-public:DescribeImages",
      "ecr-public:ListTagsForResource",
      "ecr-public:BatchCheckLayerAvailability",
      "ecr-public:GetLifecyclePolicy",
      "ecr-public:GetRepositoryPolicy",
      "ecr-public:PutImage",
      "ecr-public:InitiateLayerUpload",
      "ecr-public:UploadLayerPart",
      "ecr-public:CompleteLayerUpload",
      "ecr-public:BatchDeleteImage",
      "ecr-public:DescribeRepositories",
      "ecr-public:ListImages"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.ecr_access_for_codebuild_images.statement[2].resources) == "arn:aws:ecr-public::${data.aws_caller_identity.current.account_id}:repository/*"
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.ecr_access_for_codebase_pipeline.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.ecr_access_for_codebase_pipeline.statement[1].actions == toset([
      "ecr-public:DescribeImages"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = data.aws_iam_policy_document.ecr_access_for_codebase_pipeline.statement[1].resources == toset(["arn:aws:ecr-public::${data.aws_caller_identity.current.account_id}:repository/*"])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = length(data.aws_iam_policy_document.ecr_access_for_codebase_pipeline.statement[1].resources) == 1
    error_message = "Unexpected resources"
  }
}

run "test_deploy_repository" {
  command = plan

  variables {
    deploy_repository = "uktrade/application-deploy"
  }

  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[0].action[0].configuration.FullRepositoryId == "uktrade/application-deploy"
    error_message = "Should be: uktrade/application-deploy"
  }

  assert {
    condition     = aws_codepipeline.manual_release_pipeline.stage[0].action[0].configuration.FullRepositoryId == "uktrade/application-deploy"
    error_message = "Should be: uktrade/application-deploy"
  }
}

run "test_deploy_repository_branch" {
  command = plan

  variables {
    deploy_repository_branch = "feature-branch"
  }

  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[0].action[0].configuration.BranchName == "feature-branch"
    error_message = "Should be: feature-branch"
  }

  assert {
    condition     = aws_codepipeline.manual_release_pipeline.stage[0].action[0].configuration.BranchName == "feature-branch"
    error_message = "Should be: feature-branch"
  }
}

run "test_main_branch_filter" {
  command = plan

  variables {
    pipelines = [
      {
        name   = "main",
        branch = "main",
        environments = [
          { name = "dev" },
          { name = "prod", requires_approval = true }
        ]
      }
    ]
  }

  assert {
    condition = [
      for el in aws_codebuild_webhook.codebuild_webhook[""].filter_group : true
      if[
        for filter in el.filter : true
        if filter.type == "HEAD_REF" && filter.pattern == "^refs/heads/main$"
        ][
        0
      ] == true
      ][
      0
    ] == true
    error_message = "Should be: type = 'HEAD_REF' and pattern = '^refs/heads/main$'"
  }
}

run "test_tagged_branch_filter" {
  command = plan

  variables {
    pipelines = [
      {
        name = "tagged",
        tag  = true,
        environments = [
          { name = "staging" },
          { name = "prod", requires_approval = true }
        ]
      }
    ]
  }

  assert {
    condition = [
      for el in aws_codebuild_webhook.codebuild_webhook[""].filter_group : true
      if[
        for filter in el.filter : true
        if filter.type == "HEAD_REF" && filter.pattern == "^refs/tags/.*"
        ][
        0
      ] == true
      ][
      0
    ] == true
    error_message = "Should be: type = 'HEAD_REF' and pattern = '^refs/tags/.*'"
  }
}

run "test_iam" {
  command = plan
  # # DNS account access
  # assert {
  #   condition     = aws_iam_role.dns_account_assume_role_for_codebase_deploy[""].name == "my-app-my-codebase-codebase-image-build"
  #   error_message = "Should be: 'my-app-my-codebase-codebase-image-build'"
  # }
  assert {
    condition     = data.aws_iam_policy_document.dns_account_assume_role[""].statement[0].effect == "Allow"
    error_message = "First statement effect should be: Allow"
  }
  assert {
    condition     = length(data.aws_iam_policy_document.dns_account_assume_role[""].statement[0].resources) == 2
    error_message = "First statement effect should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.dns_account_assume_role[""].statement[0].resources == toset(
      [
        "arn:aws:iam::111123456789:role/environment-pipeline-assumed-role",
        "arn:aws:iam::222223456789:role/environment-pipeline-assumed-role"
      ]
    )
    error_message = "First statement effect should be: Allow"
  }
  assert {
    condition     = data.aws_iam_policy_document.dns_account_assume_role[""].json != null
    error_message = "Should be: "
  }
  assert {
    condition     = strcontains(jsonencode(data.aws_iam_policy_document.dns_account_assume_role[""]), "sts:AssumeRole") == true
    error_message = "Statement should not contain kms:Decrypt"
  }

  # CodeBuild image build
  assert {
    condition     = aws_iam_role.codebase_image_build[""].name == "my-app-my-codebase-codebase-image-build"
    error_message = "Should be: 'my-app-my-codebase-codebase-image-build'"
  }
  assert {
    condition     = aws_iam_role.codebase_image_build[""].assume_role_policy == "{\"Sid\": \"AssumeCodebuildRole\"}"
    error_message = "Should be: {\"Sid\": \"AssumeCodebuildRole\"}"
  }
  assert {
    condition     = jsonencode(aws_iam_role.codebase_image_build[""].tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }
  assert {
    condition     = aws_iam_role_policy.log_access_for_codebuild_images[""].name == "log-access"
    error_message = "Should be: 'log-access'"
  }
  assert {
    condition     = aws_iam_role_policy.log_access_for_codebuild_images[""].role == "my-app-my-codebase-codebase-image-build"
    error_message = "Should be: 'my-app-my-codebase-codebase-image-build'"
  }
  assert {
    condition     = aws_iam_role_policy.ecr_access_for_codebuild_images[""].name == "ecr-access"
    error_message = "Should be: 'ecr-access'"
  }
  assert {
    condition     = aws_iam_role_policy.ecr_access_for_codebuild_images[""].role == "my-app-my-codebase-codebase-image-build"
    error_message = "Should be: 'my-app-my-codebase-codebase-image-build'"
  }
  assert {
    condition     = aws_iam_role_policy.codestar_connection_access_for_codebuild_images[""].name == "codestar-connection-policy"
    error_message = "Should be: 'codestar-connection-policy'"
  }
  assert {
    condition     = aws_iam_role_policy.codestar_connection_access_for_codebuild_images[""].role == "my-app-my-codebase-codebase-image-build"
    error_message = "Should be: 'my-app-my-codebase-codebase-image-build'"
  }
  assert {
    condition     = aws_iam_role_policy_attachment.ssm_access[""].role == "my-app-my-codebase-codebase-image-build"
    error_message = "Should be: 'my-app-my-codebase-codebase-image-build'"
  }
  assert {
    condition     = aws_iam_role_policy_attachment.ssm_access[""].policy_arn == "arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess"
    error_message = "Should be: 'arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess'"
  }

  # CodeBuild deploy
  assert {
    condition     = aws_iam_role.codebase_deploy.name == "my-app-my-codebase-codebase-deploy"
    error_message = "Should be: 'my-app-my-codebase-codebase-deploy'"
  }
  assert {
    condition     = aws_iam_role.codebase_deploy.assume_role_policy == "{\"Sid\": \"AssumeCodebuildRole\"}"
    error_message = "Should be: {\"Sid\": \"AssumeCodebuildRole\"}"
  }
  assert {
    condition     = jsonencode(aws_iam_role.codebase_deploy.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }
  assert {
    condition     = aws_iam_role_policy.artifact_store_access_for_codebuild_deploy.name == "artifact-store-access"
    error_message = "Should be: 'artifact-store-access'"
  }
  assert {
    condition     = aws_iam_role_policy.artifact_store_access_for_codebuild_deploy.role == "my-app-my-codebase-codebase-deploy"
    error_message = "Should be: 'my-app-my-codebase-codebase-deploy'"
  }
  assert {
    condition     = aws_iam_role_policy.log_access_for_codebuild_deploy.name == "log-access"
    error_message = "Should be: 'log-access'"
  }
  assert {
    condition     = aws_iam_role_policy.log_access_for_codebuild_deploy.role == "my-app-my-codebase-codebase-deploy"
    error_message = "Should be: 'my-app-my-codebase-codebase-deploy'"
  }
  assert {
    condition     = aws_iam_role_policy.ecr_access_for_codebuild_deploy.name == "ecr-access"
    error_message = "Should be: 'ecr-access'"
  }
  assert {
    condition     = aws_iam_role_policy.ecr_access_for_codebuild_deploy.role == "my-app-my-codebase-codebase-deploy"
    error_message = "Should be: 'my-app-my-codebase-codebase-deploy'"
  }
  assert {
    condition     = aws_iam_role_policy.environment_deploy_role_access_for_codebuild_deploy.name == "environment-deploy-role-access"
    error_message = "Should be: 'environment-deploy-role-access'"
  }
  assert {
    condition     = aws_iam_role_policy.environment_deploy_role_access_for_codebuild_deploy.role == "my-app-my-codebase-codebase-deploy"
    error_message = "Should be: 'my-app-my-codebase-codebase-deploy'"
  }

  assert {
    condition     = aws_iam_role_policy.deploy_ssm_access.name == "deploy-ssm-access"
    error_message = "Should be: 'deploy-ssm-access'"
  }

  assert {
    condition     = aws_iam_role_policy.deploy_ssm_access.role == "my-app-my-codebase-codebase-deploy"
    error_message = "Should be: 'my-app-my-codebase-codebase-deploy'"
  }

  # CodePipeline
  assert {
    condition     = aws_iam_role.codebase_deploy_pipeline.name == "my-app-my-codebase-codebase-pipeline"
    error_message = "Should be: 'my-app-my-codebase-codebase-pipeline'"
  }
  assert {
    condition     = aws_iam_role.codebase_deploy_pipeline.assume_role_policy == "{\"Sid\": \"AssumeCodepipelineRole\"}"
    error_message = "Should be: {\"Sid\": \"AssumeCodepipelineRole\"}"
  }
  assert {
    condition     = jsonencode(aws_iam_role.codebase_deploy_pipeline.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }
  assert {
    condition     = aws_iam_role_policy.ecr_access_for_codebase_pipeline.name == "ecr-access"
    error_message = "Should be: 'ecr-access'"
  }
  assert {
    condition     = aws_iam_role_policy.ecr_access_for_codebase_pipeline.role == "my-app-my-codebase-codebase-pipeline"
    error_message = "Should be: 'my-app-my-codebase-codebase-pipeline'"
  }
  assert {
    condition     = aws_iam_role_policy.artifact_store_access_for_codebase_pipeline.name == "artifact-store-access"
    error_message = "Should be: 'artifact-store-access'"
  }
  assert {
    condition     = aws_iam_role_policy.artifact_store_access_for_codebase_pipeline.role == "my-app-my-codebase-codebase-pipeline"
    error_message = "Should be: 'my-app-my-codebase-codebase-pipeline'"
  }
  assert {
    condition     = aws_iam_role_policy.codestar_connection_access_for_codebase_pipeline.name == "codestar-connection-policy"
    error_message = "Should be: 'codestar-connection-policy'"
  }
  assert {
    condition     = aws_iam_role_policy.codestar_connection_access_for_codebase_pipeline.role == "my-app-my-codebase-codebase-pipeline"
    error_message = "Should be: 'my-app-my-codebase-codebase-pipeline'"
  }
  assert {
    condition     = aws_iam_role_policy.env_manager_access.name == "env-manager-access"
    error_message = "Should be: 'env-manager-access'"
  }
  assert {
    condition     = aws_iam_role_policy.env_manager_access.role == "my-app-my-codebase-codebase-deploy"
    error_message = "Should be: 'my-app-my-codebase-codebase-deploy'"
  }
  assert {
    condition     = aws_iam_role_policy.env_manager_access.policy == "{\"Sid\": \"AssumeEnvManagerAccess\"}"
    error_message = "Should be: {\"Sid\": \"AssumeEnvManagerAccess\"}"
  }
}

run "test_iam_documents" {
  command = plan

  # Log access
  assert {
    condition     = data.aws_iam_policy_document.log_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = data.aws_iam_policy_document.log_access.statement[0].actions == toset(["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents", "logs:TagLogGroup"])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.log_access.statement[0].resources == toset([
      "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:codebuild/my-app-my-codebase-codebase-image-build/log-group",
      "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:codebuild/my-app-my-codebase-codebase-image-build/log-group:*",
      "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:codebuild/my-app-my-codebase-codebase-deploy/log-group",
      "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:codebuild/my-app-my-codebase-codebase-deploy/log-group:*"
    ])
    error_message = "Unexpected resources"
  }

  # Assume CodeBuild role
  assert {
    condition     = data.aws_iam_policy_document.assume_codebuild_role.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.assume_codebuild_role.statement[0].actions) == "sts:AssumeRole"
    error_message = "Should be: sts:AssumeRole"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.assume_codebuild_role.statement[0].principals).type == "Service"
    error_message = "Should be: Service"
  }
  assert {
    condition     = contains(one(data.aws_iam_policy_document.assume_codebuild_role.statement[0].principals).identifiers, "codebuild.amazonaws.com")
    error_message = "Should contain: codebuild.amazonaws.com"
  }

  # ECR access
  assert {
    condition     = data.aws_iam_policy_document.ecr_access_for_codebuild_images.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.ecr_access_for_codebuild_images.statement[0].actions == toset([
      "ecr:GetAuthorizationToken",
      "ecr-public:GetAuthorizationToken",
      "sts:GetServiceBearerToken"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.ecr_access_for_codebuild_images.statement[0].resources) == "*"
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.ecr_access_for_codebuild_images.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.ecr_access_for_codebuild_images.statement[1].actions == toset([
      "ecr:DescribeImageScanFindings",
      "ecr:GetLifecyclePolicyPreview",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:DescribeImages",
      "ecr:ListTagsForResource",
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetLifecyclePolicy",
      "ecr:GetRepositoryPolicy",
      "ecr:PutImage",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
      "ecr:BatchDeleteImage",
      "ecr:DescribeRepositories",
      "ecr:ListImages"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = data.aws_iam_policy_document.ecr_access_for_codebuild_images.statement[1].resources == toset(["arn:aws:ecr:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:repository/my-app/my-codebase"])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = length(data.aws_iam_policy_document.ecr_access_for_codebuild_images.statement[1].resources) == 1
    error_message = "Unexpected resources"
  }

  # Codestar connection
  assert {
    condition     = data.aws_iam_policy_document.codestar_connection_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.codestar_connection_access.statement[0].actions == toset([
      "codestar-connections:GetConnectionToken",
      "codestar-connections:UseConnection"
    ])
    error_message = "Unexpected actions"
  }

  # Artifact store access
  assert {
    condition     = data.aws_iam_policy_document.access_artifact_store.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.access_artifact_store.statement[0].actions == toset([
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:GetBucketVersioning",
      "s3:PutObjectAcl",
      "s3:PutObject",
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = data.aws_iam_policy_document.access_artifact_store.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.access_artifact_store.statement[1].actions == toset([
      "codebuild:BatchGetBuilds",
      "codebuild:StartBuild",
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.access_artifact_store.statement[1].resources) == "*"
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.access_artifact_store.statement[2].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.access_artifact_store.statement[2].actions == toset([
      "kms:GenerateDataKey",
      "kms:Decrypt"
    ])
    error_message = "Unexpected actions"
  }

  # Assume environment deploy role
  assert {
    condition     = data.aws_iam_policy_document.environment_deploy_role_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.environment_deploy_role_access.statement[0].actions == toset([
      "sts:AssumeRole"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = flatten(data.aws_iam_policy_document.environment_deploy_role_access.statement[0].resources) == ["arn:aws:iam::000123456789:role/my-app-*-codebase-pipeline-deploy",
    "arn:aws:iam::123456789000:role/my-app-*-codebase-pipeline-deploy"]
    error_message = "Unexpected resources"
  }

  # Assume CodePipeline role
  assert {
    condition     = data.aws_iam_policy_document.assume_codepipeline_role.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.assume_codepipeline_role.statement[0].actions) == "sts:AssumeRole"
    error_message = "Should be: sts:AssumeRole"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.assume_codepipeline_role.statement[0].principals).type == "Service"
    error_message = "Should be: Service"
  }
  assert {
    condition     = contains(one(data.aws_iam_policy_document.assume_codepipeline_role.statement[0].principals).identifiers, "codepipeline.amazonaws.com")
    error_message = "Should contain: codepipeline.amazonaws.com"
  }

  # Pipeline ECR access
  assert {
    condition     = data.aws_iam_policy_document.ecr_access_for_codebase_pipeline.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.ecr_access_for_codebase_pipeline.statement[0].actions == toset([
      "ecr:DescribeImages",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = data.aws_iam_policy_document.ecr_access_for_codebase_pipeline.statement[0].resources == toset(["arn:aws:ecr:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:repository/my-app/my-codebase"])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = length(data.aws_iam_policy_document.ecr_access_for_codebase_pipeline.statement[0].resources) == 1
    error_message = "Unexpected resources"
  }

  # SSM access
  assert {
    condition     = data.aws_iam_policy_document.deploy_ssm_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.deploy_ssm_access.statement[0].actions == toset([
      "ssm:GetParameter",
      "ssm:GetParameters"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.deploy_ssm_access.statement[0].resources) == "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/codebuild/slack_*"
    error_message = "Unexpected resources"
  }

  # Copilot env manager access
  assert {
    condition     = data.aws_iam_policy_document.env_manager_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.env_manager_access.statement[0].actions == toset([
      "sts:AssumeRole"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.env_manager_access.statement[0].resources == toset([
      "arn:aws:iam::000123456789:role/my-app-*-EnvManagerRole",
      "arn:aws:iam::123456789000:role/my-app-*-EnvManagerRole"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.env_manager_access.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.env_manager_access.statement[1].actions == toset([
      "ssm:GetParameter"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.env_manager_access.statement[1].resources == toset([
      "arn:aws:ssm:eu-west-2:${data.aws_caller_identity.current.account_id}:parameter/copilot/applications/my-app",
      "arn:aws:ssm:eu-west-2:${data.aws_caller_identity.current.account_id}:parameter/copilot/applications/my-app/environments/*",
      "arn:aws:ssm:eu-west-2:${data.aws_caller_identity.current.account_id}:parameter/copilot/applications/my-app/components/*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.env_manager_access.statement[2].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.env_manager_access.statement[2].actions == toset([
      "cloudformation:GetTemplate",
      "cloudformation:GetTemplateSummary",
      "cloudformation:DescribeStackSet",
      "cloudformation:UpdateStackSet",
      "cloudformation:DescribeStackSetOperation",
      "cloudformation:ListStackInstances",
      "cloudformation:DescribeStacks",
      "cloudformation:DescribeChangeSet",
      "cloudformation:CreateChangeSet",
      "cloudformation:ExecuteChangeSet",
      "cloudformation:DescribeStackEvents",
      "cloudformation:DeleteStack"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.env_manager_access.statement[2].resources == toset([
      "arn:aws:cloudformation:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:stack/my-app-*",
      "arn:aws:cloudformation:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:stack/StackSet-my-app-infrastructure-*",
      "arn:aws:cloudformation:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:stackset/my-app-infrastructure:*",
      "arn:aws:cloudformation:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:stack/my-app-*"
    ])
    error_message = "Unexpected resources"
  }
}


run "test_codebuild_deploy" {
  command = plan

  assert {
    condition     = aws_codebuild_project.codebase_deploy.name == "my-app-my-codebase-codebase-deploy"
    error_message = "Should be: 'my-app-my-codebase-codebase-deploy'"
  }
  assert {
    condition     = aws_codebuild_project.codebase_deploy.description == "Deploy specified image tag to specified environment"
    error_message = "Should be: 'Deploy specified image tag to specified environment'"
  }
  assert {
    condition     = aws_codebuild_project.codebase_deploy.build_timeout == 30
    error_message = "Should be: 5"
  }
  assert {
    condition     = one(aws_codebuild_project.codebase_deploy.artifacts).type == "CODEPIPELINE"
    error_message = "Should be: 'CODEPIPELINE'"
  }
  assert {
    condition     = one(aws_codebuild_project.codebase_deploy.cache).type == "S3"
    error_message = "Should be: 'S3'"
  }
  assert {
    condition     = one(aws_codebuild_project.codebase_deploy.cache).location == "my-app-my-codebase-cb-arts"
    error_message = "Should be: 'my-app-my-codebase-cb-arts'"
  }
  assert {
    condition     = one(aws_codebuild_project.codebase_deploy.environment).compute_type == "BUILD_GENERAL1_SMALL"
    error_message = "Should be: 'BUILD_GENERAL1_SMALL'"
  }
  assert {
    condition     = one(aws_codebuild_project.codebase_deploy.environment).image == "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    error_message = "Should be: 'aws/codebuild/amazonlinux2-x86_64-standard:5.0'"
  }
  assert {
    condition     = one(aws_codebuild_project.codebase_deploy.environment).type == "LINUX_CONTAINER"
    error_message = "Should be: 'LINUX_CONTAINER'"
  }
  assert {
    condition     = one(aws_codebuild_project.codebase_deploy.environment).image_pull_credentials_type == "CODEBUILD"
    error_message = "Should be: 'CODEBUILD'"
  }
  assert {
    condition     = one(aws_codebuild_project.codebase_deploy.environment).environment_variable[0].name == "ENV_CONFIG"
    error_message = "Should be: 'ENV_CONFIG'"
  }
  # assert {
  #   condition     = one(aws_codebuild_project.codebase_deploy.environment).environment_variable[0].value == "{\"dev\":{\"account\":\"000123456789\",\"dns_account\": \"111123456789\"},\"prod\":{\"account\":\"123456789000\",\"dns_account\":\"222223456789\"},\"staging\":{\"account\":\"000123456789\",\"dns_account\":\"111123456789\"}}"
  #   error_message = "Incorrect value"
  # }
  assert {
    condition = aws_codebuild_project.codebase_deploy.logs_config[0].cloudwatch_logs[
      0
    ].group_name == "codebuild/my-app-my-codebase-codebase-deploy/log-group"
    error_message = "Should be: 'codebuild/my-app-my-codebase-codebase-deploy/log-group'"
  }
  assert {
    condition = aws_codebuild_project.codebase_deploy.logs_config[0].cloudwatch_logs[
      0
    ].stream_name == "codebuild/my-app-my-codebase-codebase-deploy/log-stream"
    error_message = "Should be: 'codebuild/my-app-my-codebase-codebase-deploy/log-stream'"
  }
  assert {
    condition     = one(aws_codebuild_project.codebase_deploy.source).type == "CODEPIPELINE"
    error_message = "Should be: 'CODEPIPELINE'"
  }
  assert {
    condition     = length(regexall(".*aws ecs update-service.*", aws_codebuild_project.codebase_deploy.source[0].buildspec)) > 0
    error_message = "Should contain: 'aws ecs update-service'"
  }
  assert {
    condition     = jsonencode(aws_codebuild_project.codebase_deploy.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }

  # Cloudwatch config:
  assert {
    condition     = aws_cloudwatch_log_group.codebase_deploy.name == "codebuild/my-app-my-codebase-codebase-deploy/log-group"
    error_message = "Should be: 'codebuild/my-app-my-codebase-codebase-deploy/log-group'"
  }
  assert {
    condition     = aws_cloudwatch_log_group.codebase_deploy.retention_in_days == 90
    error_message = "Should be: 90"
  }
  assert {
    condition     = aws_cloudwatch_log_stream.codebase_deploy.name == "codebuild/my-app-my-codebase-codebase-deploy/log-stream"
    error_message = "Should be: 'codebuild/my-app-my-codebase-codebase-deploy/log-stream'"
  }
  assert {
    condition     = aws_cloudwatch_log_stream.codebase_deploy.log_group_name == "codebuild/my-app-my-codebase-codebase-deploy/log-group"
    error_message = "Should be: 'codebuild/my-app-my-codebase-codebase-deploy/log-group'"
  }
}

run "test_main_pipeline" {
  command = plan

  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].name == "my-app-my-codebase-main-codebase"
    error_message = "Should be: 'my-app-my-codebase-main-codebase'"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].variable[0].name == "IMAGE_TAG"
    error_message = "Should be: 'IMAGE_TAG'"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].variable[0].default_value == "branch-main"
    error_message = "Should be: 'branch-main'"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].variable[0].description == "Tagged image in ECR to deploy"
    error_message = "Should be: 'Tagged image in ECR to deploy'"
  }
  assert {
    condition     = tolist(aws_codepipeline.codebase_pipeline[0].artifact_store)[0].location == "my-app-my-codebase-cb-arts"
    error_message = "Should be: 'my-app-my-codebase-cb-arts'"
  }
  assert {
    condition     = tolist(aws_codepipeline.codebase_pipeline[0].artifact_store)[0].type == "S3"
    error_message = "Should be: 'S3'"
  }
  assert {
    condition     = tolist(aws_codepipeline.codebase_pipeline[0].artifact_store)[0].encryption_key[0].type == "KMS"
    error_message = "Should be: 'KMS'"
  }
  assert {
    condition     = jsonencode(aws_codepipeline.codebase_pipeline[0].tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }
  assert {
    condition     = length(aws_codepipeline.codebase_pipeline[0].stage) == 2
    error_message = "Should be: 2"
  }

  # Source stage
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[0].name == "Source"
    error_message = "Should be: Source"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[0].action[0].name == "GitCheckout"
    error_message = "Should be: GitCheckout"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[0].action[0].category == "Source"
    error_message = "Should be: Source"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[0].action[0].owner == "AWS"
    error_message = "Should be: AWS"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[0].action[0].provider == "CodeStarSourceConnection"
    error_message = "Should be: CodeStarSourceConnection"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[0].action[0].version == "1"
    error_message = "Should be: 1"
  }
  assert {
    condition     = one(aws_codepipeline.codebase_pipeline[0].stage[0].action[0].output_artifacts) == "deploy_source"
    error_message = "Should be: deploy_source"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[0].action[0].configuration.FullRepositoryId == "uktrade/my-app-deploy"
    error_message = "Should be: uktrade/my-app-deploy"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[0].action[0].configuration.BranchName == "main"
    error_message = "Should be: main"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[0].action[0].configuration.DetectChanges == "false"
    error_message = "Should be: false"
  }

  # Deploy dev environment stage
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].name == "Deploy-dev"
    error_message = "Should be: Deploy-dev"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].on_failure[0].result == "ROLLBACK"
    error_message = "Should be: ROLLBACK"
  }

  # Deploy service-1 action
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[0].name == "service-1"
    error_message = "Should be: service-1"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[0].category == "Build"
    error_message = "Should be: Build"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[0].owner == "AWS"
    error_message = "Should be: AWS"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[0].provider == "CodeBuild"
    error_message = "Should be: CodeBuild"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[0].version == "1"
    error_message = "Should be: 1"
  }
  assert {
    condition     = one(aws_codepipeline.codebase_pipeline[0].stage[1].action[0].input_artifacts) == "deploy_source"
    error_message = "Should be: deploy_source"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[0].configuration.ProjectName == "my-app-my-codebase-codebase-deploy"
    error_message = "Should be: my-app-my-codebase-codebase-deploy"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.codebase_pipeline[0].stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "APPLICATION"]) == "my-app"
    error_message = "APPLICATION environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.codebase_pipeline[0].stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "AWS_REGION"]) == "${data.aws_region.current.name}"
    error_message = "AWS_REGION environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.codebase_pipeline[0].stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "AWS_ACCOUNT_ID"]) == "${data.aws_caller_identity.current.account_id}"
    error_message = "AWS_ACCOUNT_ID environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.codebase_pipeline[0].stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "ENVIRONMENT"]) == "dev"
    error_message = "ENVIRONMENT environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.codebase_pipeline[0].stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "IMAGE_TAG"]) == "#{variables.IMAGE_TAG}"
    error_message = "IMAGE_TAG environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.codebase_pipeline[0].stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "PIPELINE_EXECUTION_ID"]) == "#{codepipeline.PipelineExecutionId}"
    error_message = "PIPELINE_EXECUTION_ID environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.codebase_pipeline[0].stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "REPOSITORY_URL"]) == "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/my-app/my-codebase"
    error_message = "REPOSITORY_URL environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.codebase_pipeline[0].stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "SERVICE"]) == "service-1"
    error_message = "SERVICE environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.codebase_pipeline[0].stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "SLACK_CHANNEL_ID"]) == "/fake/slack/channel"
    error_message = "SLACK_CHANNEL_ID environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.codebase_pipeline[0].stage[1].action[0].configuration.EnvironmentVariables) :
    var.type if var.name == "SLACK_CHANNEL_ID"]) == "PARAMETER_STORE"
    error_message = "SLACK_CHANNEL_ID environment variable type is incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[0].run_order == 2
    error_message = "Run order incorrect"
  }

  # Deploy service-2 action
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[1].name == "service-2"
    error_message = "Should be: service-1"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[1].category == "Build"
    error_message = "Should be: Build"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[1].owner == "AWS"
    error_message = "Should be: AWS"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[1].provider == "CodeBuild"
    error_message = "Should be: CodeBuild"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[1].version == "1"
    error_message = "Should be: 1"
  }
  assert {
    condition     = one(aws_codepipeline.codebase_pipeline[0].stage[1].action[1].input_artifacts) == "deploy_source"
    error_message = "Should be: deploy_source"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[1].configuration.ProjectName == "my-app-my-codebase-codebase-deploy"
    error_message = "Should be: my-app-my-codebase-codebase-deploy"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.codebase_pipeline[0].stage[1].action[1].configuration.EnvironmentVariables) :
    var.value if var.name == "ENVIRONMENT"]) == "dev"
    error_message = "ENVIRONMENT environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.codebase_pipeline[0].stage[1].action[1].configuration.EnvironmentVariables) :
    var.value if var.name == "SERVICE"]) == "service-2"
    error_message = "SERVICE environment variable incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[1].run_order == 3
    error_message = "Run order incorrect"
  }
}

run "test_tagged_pipeline" {
  command = plan

  assert {
    condition     = aws_codepipeline.codebase_pipeline[1].name == "my-app-my-codebase-tagged-codebase"
    error_message = "Should be: 'my-app-my-codebase-tagged-codebase'"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[1].variable[0].default_value == "tag-latest"
    error_message = "Should be: 'tag-latest'"
  }
  assert {
    condition     = length(aws_codepipeline.codebase_pipeline[1].stage) == 3
    error_message = "Should be: 3"
  }

  # Deploy staging environment stage
  assert {
    condition     = aws_codepipeline.codebase_pipeline[1].stage[1].name == "Deploy-staging"
    error_message = "Should be: Deploy-staging"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[1].stage[1].on_failure[0].result == "ROLLBACK"
    error_message = "Should be: ROLLBACK"
  }

  # Deploy service-1 action
  assert {
    condition     = aws_codepipeline.codebase_pipeline[1].stage[1].action[0].name == "service-1"
    error_message = "Should be: service-1"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.codebase_pipeline[1].stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "ENVIRONMENT"]) == "staging"
    error_message = "ENVIRONMENT environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.codebase_pipeline[1].stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "SERVICE"]) == "service-1"
    error_message = "SERVICE environment variable incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[1].stage[1].action[0].run_order == 2
    error_message = "Run order incorrect"
  }

  # Deploy service-2 action
  assert {
    condition     = aws_codepipeline.codebase_pipeline[1].stage[1].action[1].name == "service-2"
    error_message = "Should be: service-2"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.codebase_pipeline[1].stage[1].action[1].configuration.EnvironmentVariables) :
    var.value if var.name == "ENVIRONMENT"]) == "staging"
    error_message = "ENVIRONMENT environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.codebase_pipeline[1].stage[1].action[1].configuration.EnvironmentVariables) :
    var.value if var.name == "SERVICE"]) == "service-2"
    error_message = "SERVICE environment variable incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[1].stage[1].action[1].run_order == 3
    error_message = "Run order incorrect"
  }

  # Deploy prod environment stage
  assert {
    condition     = aws_codepipeline.codebase_pipeline[1].stage[2].name == "Deploy-prod"
    error_message = "Should be: Deploy-prod"
  }

  # Approval action
  assert {
    condition     = aws_codepipeline.codebase_pipeline[1].stage[2].action[0].name == "Approve-prod"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[1].stage[2].action[0].category == "Approval"
    error_message = "Action category incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[1].stage[2].action[0].owner == "AWS"
    error_message = "Action owner incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[1].stage[2].action[0].provider == "Manual"
    error_message = "Action provider incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[1].stage[2].action[0].version == "1"
    error_message = "Action Version incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[1].stage[2].action[0].run_order == 1
    error_message = "Run order incorrect"
  }

  # Deploy service-1 action
  assert {
    condition     = aws_codepipeline.codebase_pipeline[1].stage[2].action[1].name == "service-1"
    error_message = "Should be: service-1"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.codebase_pipeline[1].stage[2].action[1].configuration.EnvironmentVariables) :
    var.value if var.name == "ENVIRONMENT"]) == "prod"
    error_message = "ENVIRONMENT environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.codebase_pipeline[1].stage[2].action[1].configuration.EnvironmentVariables) :
    var.value if var.name == "SERVICE"]) == "service-1"
    error_message = "SERVICE environment variable incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[1].stage[2].action[1].run_order == 2
    error_message = "Run order incorrect"
  }

  # Deploy service-2 action
  assert {
    condition     = aws_codepipeline.codebase_pipeline[1].stage[2].action[2].name == "service-2"
    error_message = "Should be: service-1"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.codebase_pipeline[1].stage[2].action[2].configuration.EnvironmentVariables) :
    var.value if var.name == "ENVIRONMENT"]) == "prod"
    error_message = "ENVIRONMENT environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.codebase_pipeline[1].stage[2].action[2].configuration.EnvironmentVariables) :
    var.value if var.name == "SERVICE"]) == "service-2"
    error_message = "SERVICE environment variable incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[1].stage[2].action[2].run_order == 3
    error_message = "Run order incorrect"
  }
}

run "test_manual_release_pipeline" {
  command = plan

  assert {
    condition     = aws_codepipeline.manual_release_pipeline.name == "my-app-my-codebase-manual-release"
    error_message = "Should be: 'my-app-my-codebase-manual-release'"
  }
  assert {
    condition     = aws_codepipeline.manual_release_pipeline.variable[0].name == "IMAGE_TAG"
    error_message = "Should be: 'IMAGE_TAG'"
  }
  assert {
    condition     = aws_codepipeline.manual_release_pipeline.variable[0].default_value == "NONE"
    error_message = "Should be: 'NONE'"
  }
  assert {
    condition     = aws_codepipeline.manual_release_pipeline.variable[0].description == "Tagged image in ECR to deploy"
    error_message = "Should be: 'Tagged image in ECR to deploy'"
  }
  assert {
    condition     = aws_codepipeline.manual_release_pipeline.variable[1].name == "ENVIRONMENT"
    error_message = "Should be: 'ENVIRONMENT'"
  }
  assert {
    condition     = aws_codepipeline.manual_release_pipeline.variable[1].default_value == "NONE"
    error_message = "Should be: 'NONE'"
  }
  assert {
    condition     = aws_codepipeline.manual_release_pipeline.variable[1].description == "Name of the environment to deploy to"
    error_message = "Should be: 'Name of the environment to deploy to'"
  }
  assert {
    condition     = tolist(aws_codepipeline.manual_release_pipeline.artifact_store)[0].location == "my-app-my-codebase-cb-arts"
    error_message = "Should be: 'my-app-my-codebase-cb-arts'"
  }
  assert {
    condition     = tolist(aws_codepipeline.manual_release_pipeline.artifact_store)[0].type == "S3"
    error_message = "Should be: 'S3'"
  }
  assert {
    condition     = tolist(aws_codepipeline.manual_release_pipeline.artifact_store)[0].encryption_key[0].type == "KMS"
    error_message = "Should be: 'KMS'"
  }
  assert {
    condition     = jsonencode(aws_codepipeline.manual_release_pipeline.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }
  assert {
    condition     = length(aws_codepipeline.manual_release_pipeline.stage) == 2
    error_message = "Should be: 2"
  }

  # Source stage
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[0].name == "Source"
    error_message = "Should be: Source"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[0].action[0].name == "GitCheckout"
    error_message = "Should be: GitCheckout"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[0].action[0].category == "Source"
    error_message = "Should be: Source"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[0].action[0].owner == "AWS"
    error_message = "Should be: AWS"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[0].action[0].provider == "CodeStarSourceConnection"
    error_message = "Should be: CodeStarSourceConnection"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[0].action[0].version == "1"
    error_message = "Should be: 1"
  }
  assert {
    condition     = one(aws_codepipeline.codebase_pipeline[0].stage[0].action[0].output_artifacts) == "deploy_source"
    error_message = "Should be: deploy_source"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[0].action[0].configuration.FullRepositoryId == "uktrade/my-app-deploy"
    error_message = "Should be: uktrade/my-app-deploy"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[0].action[0].configuration.BranchName == "main"
    error_message = "Should be: main"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[0].action[0].configuration.DetectChanges == "false"
    error_message = "Should be: false"
  }

  # Deploy stage
  assert {
    condition     = aws_codepipeline.manual_release_pipeline.stage[1].name == "Deploy"
    error_message = "Should be: Deploy"
  }

  # Deploy service-1 action
  assert {
    condition     = aws_codepipeline.manual_release_pipeline.stage[1].action[0].name == "service-1"
    error_message = "Should be: service-1"
  }
  assert {
    condition     = aws_codepipeline.manual_release_pipeline.stage[1].action[0].category == "Build"
    error_message = "Should be: Build"
  }
  assert {
    condition     = aws_codepipeline.manual_release_pipeline.stage[1].action[0].owner == "AWS"
    error_message = "Should be: AWS"
  }
  assert {
    condition     = aws_codepipeline.manual_release_pipeline.stage[1].action[0].provider == "CodeBuild"
    error_message = "Should be: CodeBuild"
  }
  assert {
    condition     = aws_codepipeline.manual_release_pipeline.stage[1].action[0].version == "1"
    error_message = "Should be: 1"
  }
  assert {
    condition     = one(aws_codepipeline.manual_release_pipeline.stage[1].action[0].input_artifacts) == "deploy_source"
    error_message = "Should be: deploy_source"
  }
  assert {
    condition     = aws_codepipeline.manual_release_pipeline.stage[1].action[0].configuration.ProjectName == "my-app-my-codebase-codebase-deploy"
    error_message = "Should be: my-app-my-codebase-codebase-deploy"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.manual_release_pipeline.stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "APPLICATION"]) == "my-app"
    error_message = "APPLICATION environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.manual_release_pipeline.stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "AWS_REGION"]) == "${data.aws_region.current.name}"
    error_message = "AWS_REGION environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.manual_release_pipeline.stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "AWS_ACCOUNT_ID"]) == "${data.aws_caller_identity.current.account_id}"
    error_message = "AWS_ACCOUNT_ID environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.manual_release_pipeline.stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "ENVIRONMENT"]) == "#{variables.ENVIRONMENT}"
    error_message = "ENVIRONMENT environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.manual_release_pipeline.stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "IMAGE_TAG"]) == "#{variables.IMAGE_TAG}"
    error_message = "IMAGE_TAG environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.manual_release_pipeline.stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "PIPELINE_EXECUTION_ID"]) == "#{codepipeline.PipelineExecutionId}"
    error_message = "PIPELINE_EXECUTION_ID environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.manual_release_pipeline.stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "REPOSITORY_URL"]) == "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/my-app/my-codebase"
    error_message = "REPOSITORY_URL environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.manual_release_pipeline.stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "SERVICE"]) == "service-1"
    error_message = "SERVICE environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.manual_release_pipeline.stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "SLACK_CHANNEL_ID"]) == "/fake/slack/channel"
    error_message = "SLACK_CHANNEL_ID environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.manual_release_pipeline.stage[1].action[0].configuration.EnvironmentVariables) :
    var.type if var.name == "SLACK_CHANNEL_ID"]) == "PARAMETER_STORE"
    error_message = "SLACK_CHANNEL_ID environment variable type is incorrect"
  }
  assert {
    condition     = aws_codepipeline.manual_release_pipeline.stage[1].action[0].run_order == 2
    error_message = "Run order incorrect"
  }

  # Deploy service-2 action
  assert {
    condition     = aws_codepipeline.manual_release_pipeline.stage[1].action[1].name == "service-2"
    error_message = "Should be: service-1"
  }
  assert {
    condition     = aws_codepipeline.manual_release_pipeline.stage[1].action[1].category == "Build"
    error_message = "Should be: Build"
  }
  assert {
    condition     = aws_codepipeline.manual_release_pipeline.stage[1].action[1].owner == "AWS"
    error_message = "Should be: AWS"
  }
  assert {
    condition     = aws_codepipeline.manual_release_pipeline.stage[1].action[1].provider == "CodeBuild"
    error_message = "Should be: CodeBuild"
  }
  assert {
    condition     = aws_codepipeline.manual_release_pipeline.stage[1].action[1].version == "1"
    error_message = "Should be: 1"
  }
  assert {
    condition     = one(aws_codepipeline.manual_release_pipeline.stage[1].action[1].input_artifacts) == "deploy_source"
    error_message = "Should be: deploy_source"
  }
  assert {
    condition     = aws_codepipeline.manual_release_pipeline.stage[1].action[1].configuration.ProjectName == "my-app-my-codebase-codebase-deploy"
    error_message = "Should be: my-app-my-codebase-codebase-deploy"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.manual_release_pipeline.stage[1].action[1].configuration.EnvironmentVariables) :
    var.value if var.name == "ENVIRONMENT"]) == "#{variables.ENVIRONMENT}"
    error_message = "ENVIRONMENT environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.manual_release_pipeline.stage[1].action[1].configuration.EnvironmentVariables) :
    var.value if var.name == "SERVICE"]) == "service-2"
    error_message = "SERVICE environment variable incorrect"
  }
  assert {
    condition     = aws_codepipeline.manual_release_pipeline.stage[1].action[1].run_order == 3
    error_message = "Run order incorrect"
  }
}

run "test_event_bridge" {
  command = plan

  # Main pipeline trigger
  assert {
    condition     = aws_cloudwatch_event_rule.ecr_image_publish[0].name == "my-app-my-codebase-publish-main"
    error_message = "Should be: 'my-app-my-codebase-publish-main'"
  }
  assert {
    condition     = aws_cloudwatch_event_rule.ecr_image_publish[0].description == "Trigger main deploy pipeline when an ECR image is published"
    error_message = "Should be: 'Trigger main deploy pipeline when an ECR image is published'"
  }
  assert {
    condition     = aws_cloudwatch_event_rule.ecr_image_publish[0].event_pattern == "{\"detail\":{\"action-type\":[\"PUSH\"],\"image-tag\":[\"branch-main\"],\"repository-name\":[\"my-app/my-codebase\"],\"result\":[\"SUCCESS\"]},\"detail-type\":[\"ECR Image Action\"],\"source\":[\"aws.ecr\"]}"
    error_message = "Event pattern is incorrect"
  }
  assert {
    condition     = aws_cloudwatch_event_target.codepipeline[0].rule == "my-app-my-codebase-publish-main"
    error_message = "Should be: 'my-app-my-codebase-publish-main'"
  }

  # Tagged pipeline trigger
  assert {
    condition     = aws_cloudwatch_event_rule.ecr_image_publish[1].name == "my-app-my-codebase-publish-tagged"
    error_message = "Should be: 'my-app-my-codebase-publish-tagged'"
  }
  assert {
    condition     = aws_cloudwatch_event_rule.ecr_image_publish[1].description == "Trigger tagged deploy pipeline when an ECR image is published"
    error_message = "Should be: 'Trigger tagged deploy pipeline when an ECR image is published'"
  }
  assert {
    condition     = aws_cloudwatch_event_rule.ecr_image_publish[1].event_pattern == "{\"detail\":{\"action-type\":[\"PUSH\"],\"image-tag\":[\"tag-latest\"],\"repository-name\":[\"my-app/my-codebase\"],\"result\":[\"SUCCESS\"]},\"detail-type\":[\"ECR Image Action\"],\"source\":[\"aws.ecr\"]}"
    error_message = "Event pattern is incorrect"
  }
  assert {
    condition     = aws_cloudwatch_event_target.codepipeline[1].rule == "my-app-my-codebase-publish-tagged"
    error_message = "Should be: 'my-app-my-codebase-publish-tagged'"
  }

  # IAM roles
  assert {
    condition     = aws_iam_role.event_bridge_pipeline_trigger[""].name == "my-app-my-codebase-pipeline-trigger"
    error_message = "Should be: 'my-app-my-codebase-pipeline-trigger'"
  }
  assert {
    condition     = aws_iam_role.event_bridge_pipeline_trigger[""].assume_role_policy == "{\"Sid\": \"AssumeEventBridge\"}"
    error_message = "Should be: {\"Sid\": \"AssumeEventBridge\"}"
  }
  assert {
    condition     = jsonencode(aws_iam_role.event_bridge_pipeline_trigger[""].tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }
  assert {
    condition     = aws_iam_role_policy.event_bridge_pipeline_trigger[""].name == "event-bridge-access"
    error_message = "Should be: 'event-bridge-access'"
  }
  assert {
    condition     = aws_iam_role_policy.event_bridge_pipeline_trigger[""].role == "my-app-my-codebase-pipeline-trigger"
    error_message = "Should be: 'my-app-my-codebase-pipeline-trigger'"
  }
  assert {
    condition     = aws_iam_role_policy.event_bridge_pipeline_trigger[""].policy == "{\"Sid\": \"EventBridgePipelineTrigger\"}"
    error_message = "Unexpected policy"
  }

  # IAM Policy documents
  assert {
    condition     = data.aws_iam_policy_document.event_bridge_pipeline_trigger.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.event_bridge_pipeline_trigger.statement[0].actions) == "codepipeline:StartPipelineExecution"
    error_message = "Should be: codepipeline:StartPipelineExecution"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.event_bridge_pipeline_trigger.statement[0].resources) == "arn:aws:codepipeline:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:my-app-my-codebase-main-codebase"
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.assume_event_bridge_policy.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.assume_event_bridge_policy.statement[0].actions) == "sts:AssumeRole"
    error_message = "Should be: sts:AssumeRole"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.assume_event_bridge_policy.statement[0].principals).type == "Service"
    error_message = "Should be: Service"
  }
  assert {
    condition     = contains(one(data.aws_iam_policy_document.assume_event_bridge_policy.statement[0].principals).identifiers, "events.amazonaws.com")
    error_message = "Should contain: events.amazonaws.com"
  }
}

run "test_pipeline_single_run_group" {
  command = plan

  variables {
    services = [
      {
        "run_group_1" : [
          "service-1",
          "service-2",
          "service-3",
          "service-4"
        ]
      }
    ]
  }

  # service-1
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[0].name == "service-1"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[0].run_order == 2
    error_message = "Run order incorrect"
  }

  # service-2
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[1].name == "service-2"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[1].run_order == 2
    error_message = "Run order incorrect"
  }

  # service-3
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[2].name == "service-3"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[2].run_order == 2
    error_message = "Run order incorrect"
  }

  # service-4
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[3].name == "service-4"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[3].run_order == 2
    error_message = "Run order incorrect"
  }
}

run "test_pipeline_multiple_run_groups" {
  command = plan

  variables {
    services = [
      {
        "run_group_1" : [
          "service-1"
        ]
      },
      {
        "run_group_2" : [
          "service-2",
          "service-3"
        ]
      },
      {
        "run_group_3" : [
          "service-4"
        ]
      },
      {
        "run_group_4" : [
          "service-5",
          "service-6",
          "service-7"
        ]
      }
    ]
  }

  # service-1
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[0].name == "service-1"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[0].run_order == 2
    error_message = "Run order incorrect"
  }

  # service-2
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[1].name == "service-2"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[1].run_order == 3
    error_message = "Run order incorrect"
  }

  # service-3
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[2].name == "service-3"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[2].run_order == 3
    error_message = "Run order incorrect"
  }

  # service-4
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[3].name == "service-4"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[3].run_order == 4
    error_message = "Run order incorrect"
  }

  # service-5
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[4].name == "service-5"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[4].run_order == 5
    error_message = "Run order incorrect"
  }

  # service-6
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[5].name == "service-6"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[5].run_order == 5
    error_message = "Run order incorrect"
  }

  # service-7
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[6].name == "service-7"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[6].run_order == 5
    error_message = "Run order incorrect"
  }
}

run "test_pipeline_multiple_run_groups_multiple_environment_approval" {
  command = plan

  variables {
    services = [
      {
        "run_group_1" : [
          "service-1"
        ]
      },
      {
        "run_group_2" : [
          "service-2",
          "service-3"
        ]
      },
      {
        "run_group_3" : [
          "service-4"
        ]
      }
    ]
    pipelines = [
      {
        name   = "main",
        branch = "main",
        environments = [
          { name = "dev" },
          { name = "prod", requires_approval = true }
        ]
      }
    ]
  }

  # Dev
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].name == "Deploy-dev"
    error_message = "Should be: Deploy-dev"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].on_failure[0].result == "ROLLBACK"
    error_message = "Should be: ROLLBACK"
  }

  # service-1
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[0].name == "service-1"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[0].run_order == 2
    error_message = "Run order incorrect"
  }

  # service-2
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[1].name == "service-2"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[1].run_order == 3
    error_message = "Run order incorrect"
  }

  # service-3
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[2].name == "service-3"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[2].run_order == 3
    error_message = "Run order incorrect"
  }

  # service-4
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[3].name == "service-4"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[1].action[3].run_order == 4
    error_message = "Run order incorrect"
  }

  # Prod
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[2].name == "Deploy-prod"
    error_message = "Should be: Deploy-prod"
  }

  # Approval
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[2].action[0].name == "Approve-prod"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[2].action[0].run_order == 1
    error_message = "Run order incorrect"
  }

  # service-1
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[2].action[1].name == "service-1"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[2].action[1].run_order == 2
    error_message = "Run order incorrect"
  }

  # service-2
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[2].action[2].name == "service-2"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[2].action[2].run_order == 3
    error_message = "Run order incorrect"
  }

  # service-3
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[2].action[3].name == "service-3"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[2].action[3].run_order == 3
    error_message = "Run order incorrect"
  }

  # service-4
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[2].action[4].name == "service-4"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.codebase_pipeline[0].stage[2].action[4].run_order == 4
    error_message = "Run order incorrect"
  }
}

run "test_ssm_parameter" {
  command = plan

  assert {
    condition     = aws_ssm_parameter.codebase_config.name == "/copilot/applications/my-app/codebases/my-codebase"
    error_message = "Should be: /copilot/applications/my-app/codebases/my-codebase"
  }
  assert {
    condition     = aws_ssm_parameter.codebase_config.type == "String"
    error_message = "Should be: String"
  }
  assert {
    condition     = jsondecode(aws_ssm_parameter.codebase_config.value).name == "my-codebase"
    error_message = "Should be: my-codebase"
  }
  assert {
    condition     = jsondecode(aws_ssm_parameter.codebase_config.value).repository == "my-repository"
    error_message = "Should be: my-repository"
  }
  assert {
    condition     = jsondecode(aws_ssm_parameter.codebase_config.value).deploy_repository_branch == "main"
    error_message = "Should be: main"
  }
  assert {
    condition     = jsondecode(aws_ssm_parameter.codebase_config.value).additional_ecr_repository == null
    error_message = "Should be: null"
  }
  assert {
    condition     = jsondecode(aws_ssm_parameter.codebase_config.value).slack_channel == "/fake/slack/channel"
    error_message = "Should be: /fake/slack/channel"
  }
  assert {
    condition     = jsondecode(aws_ssm_parameter.codebase_config.value).requires_image_build == true
    error_message = "Should be: true"
  }
  assert {
    condition = jsondecode(aws_ssm_parameter.codebase_config.value).services == [
      {
        "run_group_1" : [
          "service-1"
        ]
      },
      {
        "run_group_2" : [
          "service-2"
        ]
      }
    ]
    error_message = "Unexpected services"
  }
  assert {
    condition     = jsondecode(aws_ssm_parameter.codebase_config.value).pipelines[0].name == "main"
    error_message = "Should be main"
  }
  assert {
    condition     = jsondecode(aws_ssm_parameter.codebase_config.value).pipelines[0].branch == "main"
    error_message = "Should be main"
  }
  assert {
    condition     = jsondecode(aws_ssm_parameter.codebase_config.value).pipelines[0].environments[0].name == "dev"
    error_message = "Should be dev"
  }
  assert {
    condition     = jsondecode(aws_ssm_parameter.codebase_config.value).pipelines[1].name == "tagged"
    error_message = "Should be tagged"
  }
  assert {
    condition     = jsondecode(aws_ssm_parameter.codebase_config.value).pipelines[1].tag == true
    error_message = "Should be true"
  }
  assert {
    condition     = jsondecode(aws_ssm_parameter.codebase_config.value).pipelines[1].environments[0].name == "staging"
    error_message = "Should be staging"
  }
  assert {
    condition     = jsondecode(aws_ssm_parameter.codebase_config.value).pipelines[1].environments[1].name == "prod"
    error_message = "Should be prod"
  }
  assert {
    condition     = jsondecode(aws_ssm_parameter.codebase_config.value).pipelines[1].environments[1].requires_approval == true
    error_message = "Should be true"
  }
  assert {
    condition     = jsonencode(aws_ssm_parameter.codebase_config.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }
}
