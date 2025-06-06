mock_provider "aws" {}

override_data {
  target = data.aws_iam_policy_document.assume_codepipeline_role
  values = {
    json = "{\"Sid\": \"AssumePipelineRole\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.assume_codebuild_role
  values = {
    json = "{\"Sid\": \"AssumeCodebuildRole\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.ssm_access
  values = {
    json = "{\"Sid\": \"SSMAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.log_access
  values = {
    json = "{\"Sid\": \"LogAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.environment_deploy_role_access
  values = {
    json = "{\"Sid\": \"EnvDeployRoleAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.access_artifact_store
  values = {
    json = "{\"Sid\": \"AccessArtifactStore\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.codestar_connection_access
  values = {
    json = "{\"Sid\": \"CodestarConnectionAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.codepipeline_access
  values = {
    json = "{\"Sid\": \"CodepipelineAccess\"}"
  }
}

variables {
  application       = "my-app"
  deploy_repository = "my-repository"
  pipeline_name     = "my-pipeline"
  environments = {
    "dev" : null
    "prod" = {
      requires_approval = true
    }
  }

  expected_tags = {
    application         = "my-app"
    copilot-application = "my-app"
    managed-by          = "DBT Platform - Terraform"
  }

  env_config = {
    "*" = {
      accounts = {
        deploy = {
          name = "sandbox"
          id   = "000123456789"
        }
        dns = {
          name = "dev"
          id   = "000987654321"
        }
      }
      vpc : "platform-sandbox-dev"
    },
    "dev" = null,
    "prod" = {
      accounts = {
        deploy = {
          name = "prod"
          id   = "123456789000"
        }
        dns = {
          name = "live"
          id   = "987654321000"
        }
      }
      vpc : "platform-sandbox-prod"
    }
  }
}

run "test_code_pipeline" {
  command = plan

  assert {
    condition     = aws_codepipeline.environment_pipeline.name == "my-app-my-pipeline-environment-pipeline"
    error_message = "Should be: my-app-my-pipeline-environment-pipeline"
  }
  # aws_codepipeline.environment_pipeline.role_arn cannot be tested on a plan
  assert {
    condition     = aws_codepipeline.environment_pipeline.variable[0].name == "PLATFORM_HELPER_VERSION_OVERRIDE"
    error_message = "Should be: 'PLATFORM_HELPER_VERSION_OVERRIDE'"
  }

  assert {
    condition     = aws_codepipeline.environment_pipeline.variable[0].default_value == "NONE"
    error_message = "Should be: 'NONE'"
  }

  assert {
    condition     = aws_codepipeline.environment_pipeline.variable[0].description == "Override the platform-helper default version specified in platform-config"
    error_message = "Should be: 'Override the platform-helper default version specified in platform-config'"
  }

  assert {
    condition     = tolist(aws_codepipeline.environment_pipeline.artifact_store)[0].location == "my-app-my-pipeline-environment-pipeline-artifact-store"
    error_message = "Should be: my-app-my-pipeline-environment-pipeline-artifact-store"
  }
  assert {
    condition     = tolist(aws_codepipeline.environment_pipeline.artifact_store)[0].type == "S3"
    error_message = "Should be: S3"
  }
  # aws_codepipeline.environment_pipeline.artifact_store.encryption_key.id cannot be tested on a plan
  assert {
    condition     = tolist(aws_codepipeline.environment_pipeline.artifact_store)[0].encryption_key[0].type == "KMS"
    error_message = "Should be: KMS"
  }

  # Source stage
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[0].name == "Source"
    error_message = "Should be: Source"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[0].action[0].name == "GitCheckout"
    error_message = "Should be: Git checkout"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[0].action[0].category == "Source"
    error_message = "Should be: Source"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[0].action[0].owner == "AWS"
    error_message = "Should be: AWS"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[0].action[0].provider == "CodeStarSourceConnection"
    error_message = "Should be: CodeStarSourceConnection"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[0].action[0].version == "1"
    error_message = "Should be: 1"
  }
  assert {
    condition     = one(aws_codepipeline.environment_pipeline.stage[0].action[0].output_artifacts) == "project_deployment_source"
    error_message = "Should be: source_output"
  }
  # aws_codepipeline.environment_pipeline.stage[0].action[0].configuration.ConnectionArn cannot be tested on a plan
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[0].action[0].configuration.FullRepositoryId == "my-repository"
    error_message = "Should be: my-repository"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[0].action[0].configuration.BranchName == "main"
    error_message = "Should be: main"
  }

  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[0].action[0].configuration.DetectChanges == "true"
    error_message = "Should be: true"
  }

  # Build stage
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[1].name == "Install-Build-Tools"
    error_message = "Should be: Install-Build-Tools"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[1].action[0].name == "InstallTools"
    error_message = "Should be: InstallTools"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[1].action[0].category == "Build"
    error_message = "Should be: Build"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[1].action[0].owner == "AWS"
    error_message = "Should be: AWS"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[1].action[0].provider == "CodeBuild"
    error_message = "Should be: CodeBuild"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[1].action[0].version == "1"
    error_message = "Should be: 1"
  }
  assert {
    condition     = one(aws_codepipeline.environment_pipeline.stage[1].action[0].input_artifacts) == "project_deployment_source"
    error_message = "Should be: project_deployment_source"
  }
  assert {
    condition     = one(aws_codepipeline.environment_pipeline.stage[1].action[0].output_artifacts) == "build_output"
    error_message = "Should be: build_output"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[1].action[0].configuration.ProjectName == "my-app-my-pipeline-environment-pipeline-build"
    error_message = "Should be: my-app-my-pipeline-environment-pipeline-build"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[1].action[0].configuration.PrimarySource == "project_deployment_source"
    error_message = "Should be: project_deployment_source"
  }

  # Tags
  assert {
    condition     = jsonencode(aws_codepipeline.environment_pipeline.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }
}

run "test_pipeline_trigger_setup" {
  command = plan

  variables {
    trigger_on_push = false
  }

  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[0].action[0].configuration.DetectChanges == "false"
    error_message = "Should be: false"
  }

  assert {
    condition     = contains(aws_codepipeline.environment_pipeline.trigger[0].git_configuration[0].push[0].branches[0].includes, "NO_TRIGGER")
    error_message = "Should be: NO_TRIGGER"
  }

  assert {
    condition     = length(aws_codepipeline.environment_pipeline.trigger[0].git_configuration[0].push[0].branches[0].includes) == 1
    error_message = "The pipeline trigger should only have one push branch listed"
  }
}

run "test_pipeline_trigger_branch" {
  command = plan

  variables {
    deploy_repository_branch = "my-branch"
    trigger_on_push          = true
  }

  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[0].action[0].configuration.BranchName == "my-branch"
    error_message = "Should be: my-branch"
  }

  assert {
    condition     = aws_codepipeline.environment_pipeline.trigger[0].provider_type == "CodeStarSourceConnection"
    error_message = "Should be: CodeStarSourceConnection"
  }

  assert {
    condition     = aws_codepipeline.environment_pipeline.trigger[0].git_configuration[0].source_action_name == "GitCheckout"
    error_message = "Should be: GitCheckout"
  }

  assert {
    condition     = contains(aws_codepipeline.environment_pipeline.trigger[0].git_configuration[0].push[0].branches[0].includes, "my-branch")
    error_message = "Should be: my-branch"
  }

  assert {
    condition     = length(aws_codepipeline.environment_pipeline.trigger[0].git_configuration[0].push[0].branches[0].includes) == 1
    error_message = "The pipeline trigger should only have one push branch listed"
  }
}

run "test_codebuild" {
  command = plan

  assert {
    condition     = aws_codebuild_project.environment_pipeline_build.name == "my-app-my-pipeline-environment-pipeline-build"
    error_message = "Should be: my-app-my-pipeline-environment-pipeline-build"
  }
  assert {
    condition     = aws_codebuild_project.environment_pipeline_build.description == "Provisions the my-app application's extensions."
    error_message = "Should be: 'Provisions the my-app application's extensions.'"
  }
  assert {
    condition     = aws_codebuild_project.environment_pipeline_build.build_timeout == 5
    error_message = "Should be: 5"
  }
  assert {
    condition     = one(aws_codebuild_project.environment_pipeline_build.artifacts).type == "CODEPIPELINE"
    error_message = "Should be: 'CODEPIPELINE'"
  }
  assert {
    condition     = one(aws_codebuild_project.environment_pipeline_build.cache).type == "S3"
    error_message = "Should be: 'S3'"
  }
  assert {
    condition     = one(aws_codebuild_project.environment_pipeline_build.cache).location == "my-app-my-pipeline-environment-pipeline-artifact-store"
    error_message = "Should be: 'my-app-my-pipeline-environment-pipeline-artifact-store'"
  }
  assert {
    condition     = one(aws_codebuild_project.environment_pipeline_build.environment).compute_type == "BUILD_GENERAL1_SMALL"
    error_message = "Should be: 'BUILD_GENERAL1_SMALL'"
  }
  assert {

    condition     = one(aws_codebuild_project.environment_pipeline_build.environment).image == "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    error_message = "Should be: 'aws/codebuild/amazonlinux2-x86_64-standard:5.0'"
  }
  assert {
    condition     = one(aws_codebuild_project.environment_pipeline_build.environment).type == "LINUX_CONTAINER"
    error_message = "Should be: 'LINUX_CONTAINER'"
  }
  assert {
    condition     = one(aws_codebuild_project.environment_pipeline_build.environment).image_pull_credentials_type == "CODEBUILD"
    error_message = "Should be: 'CODEBUILD'"
  }
  assert {
    condition     = aws_codebuild_project.environment_pipeline_build.logs_config[0].cloudwatch_logs[0].group_name == "codebuild/my-app-my-pipeline-environment-terraform/log-group"
    error_message = "Should be: 'codebuild/my-app-my-pipeline-environment-terraform/log-group'"
  }
  assert {
    condition     = aws_codebuild_project.environment_pipeline_build.logs_config[0].cloudwatch_logs[0].stream_name == "codebuild/my-app-my-pipeline-environment-terraform/log-stream"
    error_message = "Should be: 'codebuild/my-app-my-pipeline-environment-terraform/log-group'"
  }
  assert {
    condition     = one(aws_codebuild_project.environment_pipeline_build.source).type == "CODEPIPELINE"
    error_message = "Should be: 'CODEPIPELINE'"
  }
  assert {
    condition     = length(regexall(".*echo \"Installing build tools\".*", aws_codebuild_project.environment_pipeline_build.source[0].buildspec)) > 0
    error_message = "Should contain: 'echo \"Installing build tools\"'"
  }
  assert {
    condition     = jsonencode(aws_codebuild_project.environment_pipeline_build.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }

  # Cloudwatch config:
  assert {
    condition     = aws_cloudwatch_log_group.environment_pipeline_codebuild.name == "codebuild/my-app-my-pipeline-environment-terraform/log-group"
    error_message = "Should be: 'codebuild/my-app-my-pipeline-environment-terraform/log-group'"
  }
  assert {
    condition     = aws_cloudwatch_log_group.environment_pipeline_codebuild.retention_in_days == 90
    error_message = "Should be: 90"
  }
  assert {
    condition     = aws_cloudwatch_log_stream.environment_pipeline_codebuild.name == "codebuild/my-app-my-pipeline-environment-terraform/log-stream"
    error_message = "Should be: 'codebuild/my-app-my-pipeline-environment-terraform/log-stream'"
  }
  assert {
    condition     = aws_cloudwatch_log_stream.environment_pipeline_codebuild.log_group_name == "codebuild/my-app-my-pipeline-environment-terraform/log-group"
    error_message = "Should be: 'codebuild/my-app-my-pipeline-environment-terraform/log-group'"
  }
}

run "test_iam" {
  command = plan

  # IAM Role for the pipeline.
  assert {
    condition     = aws_iam_role.environment_pipeline_codepipeline.name == "my-app-my-pipeline-environment-pipeline-codepipeline"
    error_message = "Should be: 'my-app-my-pipeline-environment-pipeline-codepipeline'"
  }
  assert {
    condition     = aws_iam_role.environment_pipeline_codepipeline.assume_role_policy == "{\"Sid\": \"AssumePipelineRole\"}"
    error_message = "Should be: {\"Sid\": \"AssumePipelineRole\"}"
  }
  assert {
    condition     = jsonencode(aws_iam_role.environment_pipeline_codepipeline.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }
  assert {
    condition     = aws_iam_role_policy.artifact_store_access_for_environment_pipeline.name == "artifact-store-access"
    error_message = "Should be: 'artifact-store-access'"
  }
  assert {
    condition     = aws_iam_role_policy.artifact_store_access_for_environment_pipeline.role == "my-app-my-pipeline-environment-pipeline-codepipeline"
    error_message = "Should be: 'my-app-my-pipeline-environment-pipeline-codepipeline'"
  }
  assert {
    condition     = aws_iam_role_policy.codestar_connection_access_for_environment_pipeline.name == "codestar-connection-access"
    error_message = "Should be: 'codestar-connection-access'"
  }
  assert {
    condition     = aws_iam_role_policy.codestar_connection_access_for_environment_pipeline.role == "my-app-my-pipeline-environment-pipeline-codepipeline"
    error_message = "Should be: 'my-app-my-pipeline-environment-pipeline-codepipeline'"
  }

  # IAM Role for the codebuild
  assert {
    condition     = aws_iam_role.environment_pipeline_codebuild.name == "my-app-my-pipeline-environment-pipeline-codebuild"
    error_message = "Should be: 'my-app-my-pipeline-environment-pipeline-codebuild'"
  }
  assert {
    condition     = aws_iam_role.environment_pipeline_codebuild.assume_role_policy == "{\"Sid\": \"AssumeCodebuildRole\"}"
    error_message = "Should be: {\"Sid\": \"AssumeCodebuildRole\"}"
  }
  assert {
    condition     = jsonencode(aws_iam_role.environment_pipeline_codebuild.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }
  assert {
    condition     = aws_iam_role_policy.artifact_store_access_for_environment_codebuild.name == "artifact-store-access"
    error_message = "Should be: 'artifact-store-access'"
  }
  assert {
    condition     = aws_iam_role_policy.artifact_store_access_for_environment_codebuild.role == "my-app-my-pipeline-environment-pipeline-codebuild"
    error_message = "Should be: 'my-app-my-pipeline-environment-pipeline-codebuild'"
  }
  assert {
    condition     = aws_iam_role_policy.log_access_for_environment_codebuild.name == "log-access"
    error_message = "Should be: 'log-access'"
  }
  assert {
    condition     = aws_iam_role_policy.log_access_for_environment_codebuild.role == "my-app-my-pipeline-environment-pipeline-codebuild"
    error_message = "Should be: 'my-app-my-pipeline-environment-pipeline-codebuild'"
  }
  assert {
    condition     = aws_iam_role_policy.ssm_access_for_environment_codebuild.name == "ssm-access"
    error_message = "Should be: 'ssm-access'"
  }
  assert {
    condition     = aws_iam_role_policy.ssm_access_for_environment_codebuild.role == "my-app-my-pipeline-environment-pipeline-codebuild"
    error_message = "Should be: 'my-app-my-pipeline-environment-pipeline-codebuild'"
  }
  assert {
    condition     = aws_iam_role_policy.codepipeline_access_for_environment_codebuild.name == "codepipeline-access"
    error_message = "Should be: 'codepipeline-access'"
  }
  assert {
    condition     = aws_iam_role_policy.codepipeline_access_for_environment_codebuild.role == "my-app-my-pipeline-environment-pipeline-codebuild"
    error_message = "Should be: 'my-app-my-pipeline-environment-pipeline-codebuild'"
  }
  assert {
    condition     = aws_iam_role_policy.environment_deploy_role_access_for_environment_codebuild.name == "environment-deploy-role-access"
    error_message = "Should be: 'environment-deploy-role-access'"
  }
  assert {
    condition     = aws_iam_role_policy.environment_deploy_role_access_for_environment_codebuild.role == "my-app-my-pipeline-environment-pipeline-codebuild"
    error_message = "Should be: 'my-app-my-pipeline-environment-pipeline-codebuild'"
  }
}

run "test_iam_documents" {
  command = plan

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
      "kms:GenerateDataKey",
      "kms:Decrypt"
    ])
    error_message = "Unexpected actions"
  }

  # Codestar connection access
  assert {
    condition     = data.aws_iam_policy_document.codestar_connection_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.codestar_connection_access.statement[0].actions == toset([
      "codestar-connections:UseConnection",
      "codestar-connections:ListConnections",
      "codestar-connections:ListTagsForResource",
      "codestar-connections:PassConnection"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = flatten(data.aws_iam_policy_document.codestar_connection_access.statement[0].resources) == [
      "arn:aws:codestar-connections:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"
    ]
    error_message = "Unexpected resources "
  }
  assert {
    condition     = data.aws_iam_policy_document.codestar_connection_access.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.codestar_connection_access.statement[1].actions == toset([
      "codebuild:BatchGetBuilds",
      "codebuild:StartBuild",
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.codestar_connection_access.statement[1].resources) == "*"
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
  assert {
    condition     = one([for el in data.aws_iam_policy_document.assume_codebuild_role.statement[0].condition : el.test]) == "StringEquals"
    error_message = "Policy condition incorrect"
  }
  assert {
    condition     = [for el in data.aws_iam_policy_document.assume_codebuild_role.statement[0].condition : el.variable][0] == "aws:SourceArn"
    error_message = "Policy condition incorrect"
  }
  assert {
    condition = flatten([for el in data.aws_iam_policy_document.assume_codebuild_role.statement[0].condition : el.values]) == [
      "arn:aws:codebuild:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:project/my-app-my-pipeline-environment-pipeline-plan",
      "arn:aws:codebuild:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:project/my-app-my-pipeline-environment-pipeline-build",
      "arn:aws:codebuild:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:project/my-app-my-pipeline-environment-pipeline-apply"
    ]
    error_message = "Policy condition incorrect ${jsonencode(flatten([for el in data.aws_iam_policy_document.assume_codebuild_role.statement[0].condition : el.values]))}"
  }

  # Log access
  assert {
    condition     = data.aws_iam_policy_document.log_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.log_access.statement[0].actions == toset([
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:TagLogGroup"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.log_access.statement[0].resources == toset([
      "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:codebuild/my-app-my-pipeline-environment-terraform/log-group",
      "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:codebuild/my-app-my-pipeline-environment-terraform/log-group:*"
    ])
    error_message = "Unexpected resources"
  }

  # SSM access
  assert {
    condition     = data.aws_iam_policy_document.ssm_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.ssm_access.statement[0].actions == toset([
      "ssm:GetParameter",
      "ssm:GetParameters"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.ssm_access.statement[0].resources == toset([
      "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/codebuild/slack_*"
    ])
    error_message = "Unexpected resources"
  }

  # Codepipeline access
  assert {
    condition     = data.aws_iam_policy_document.codepipeline_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.codepipeline_access.statement[0].actions == toset([
      "codepipeline:GetPipelineState",
      "codepipeline:GetPipelineExecution",
      "codepipeline:ListPipelineExecutions",
      "codepipeline:StopPipelineExecution",
      "codepipeline:UpdatePipeline"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.codepipeline_access.statement[0].resources == toset([
      "arn:aws:codepipeline:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:${var.application}-${var.pipeline_name}-environment-pipeline"
    ])
    error_message = "Unexpected resources"
  }

  # Deploy role access
  assert {
    condition     = data.aws_iam_policy_document.environment_deploy_role_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.environment_deploy_role_access.statement[0].actions) == "sts:AssumeRole"
    error_message = "Should be: sts:AssumeRole"
  }
  assert {
    condition = data.aws_iam_policy_document.environment_deploy_role_access.statement[0].resources == toset([
      "arn:aws:iam::000123456789:role/my-app-dev-environment-pipeline-deploy",
      "arn:aws:iam::123456789000:role/my-app-prod-environment-pipeline-deploy"
    ])
    error_message = "Unexpected resources"
  }
}

run "test_artifact_store" {
  command = plan

  assert {
    condition     = aws_s3_bucket.artifact_store.bucket == "my-app-my-pipeline-environment-pipeline-artifact-store"
    error_message = "Should be: my-app-my-pipeline-environment-pipeline-artifact-store"
  }
  assert {
    condition     = aws_kms_alias.artifact_store_kms_alias.name == "alias/my-app-my-pipeline-environment-pipeline-artifact-store-key"
    error_message = "Should be: alias/my-app-my-pipeline-environment-pipeline-artifact-store-key"
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
    condition = flatten([for el in data.aws_iam_policy_document.artifact_store_bucket_policy.statement[1].condition : el.values]) == [
      "arn:aws:iam::000123456789:role/my-app-dev-environment-pipeline-deploy",
      "arn:aws:iam::123456789000:role/my-app-prod-environment-pipeline-deploy"
    ]
    error_message = "Bucket policy condition incorrect"
  }
  assert {
    condition     = [for el in data.aws_iam_policy_document.artifact_store_bucket_policy.statement[1].actions : el][0] == "s3:*"
    error_message = "Should be: s3:*"
  }
}

run "test_stages" {
  command = plan

  assert {
    condition     = length(aws_codepipeline.environment_pipeline.stage) == 7
    error_message = "Should be: 7"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[0].name == "Source"
    error_message = "Should be: Source"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[1].name == "Install-Build-Tools"
    error_message = "Should be: Install-Build-Tools"
  }

  # Stage: dev plan
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[2].name == "Plan-dev"
    error_message = "Should be: Plan-dev"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[2].action[0].name == "Plan"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[2].action[0].category == "Build"
    error_message = "Action category incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[2].action[0].owner == "AWS"
    error_message = "Action owner incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[2].action[0].provider == "CodeBuild"
    error_message = "Action provider incorrect"
  }
  assert {
    condition     = length(aws_codepipeline.environment_pipeline.stage[2].action[0].input_artifacts) == 1
    error_message = "Input artifacts incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[2].action[0].input_artifacts[0] == "build_output"
    error_message = "Input artifacts incorrect"
  }
  assert {
    condition     = length(aws_codepipeline.environment_pipeline.stage[2].action[0].output_artifacts) == 1
    error_message = "Output artifacts incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[2].action[0].output_artifacts[0] == "dev_terraform_plan"
    error_message = "Output artifacts incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[2].action[0].version == "1"
    error_message = "Action Version incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[2].action[0].configuration.ProjectName == "my-app-my-pipeline-environment-pipeline-plan"
    error_message = "Configuration ProjectName incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[2].action[0].configuration.PrimarySource == "build_output"
    error_message = "Configuration PrimarySource incorrect"
  }

  assert {
    condition = one([for var in jsondecode(aws_codepipeline.environment_pipeline.stage[2].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "APPLICATION"]) == "my-app"
    error_message = "APPLICATION environment variable incorrect"
  }

  assert {
    condition = one([for var in jsondecode(aws_codepipeline.environment_pipeline.stage[2].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "ENVIRONMENT"]) == "dev"
    error_message = "ENVIRONMENT environment variable incorrect"
  }

  assert {
    condition = one([for var in jsondecode(aws_codepipeline.environment_pipeline.stage[2].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "PIPELINE_NAME"]) == "my-pipeline"
    error_message = "PIPELINE_NAME environment variable incorrect"
  }

  assert {
    condition = one([for var in jsondecode(aws_codepipeline.environment_pipeline.stage[2].action[0].configuration.EnvironmentVariables) :
    var.type if var.name == "SLACK_CHANNEL_ID"]) == "PARAMETER_STORE"
    error_message = "SLACK_CHANNEL_ID environment variable incorrect"
  }

  assert {
    condition = one([for var in jsondecode(aws_codepipeline.environment_pipeline.stage[2].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "SLACK_CHANNEL_ID"]) == "/codebuild/slack_pipeline_notifications_channel"
    error_message = "SLACK_CHANNEL_ID environment variable incorrect"
  }

  assert {
    condition = one([for var in jsondecode(aws_codepipeline.environment_pipeline.stage[2].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "SLACK_REF"]) == "#{slack.SLACK_REF}"
    error_message = "SLACK_REF environment variable incorrect"
  }

  assert {
    condition = one([for var in jsondecode(aws_codepipeline.environment_pipeline.stage[2].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "NEEDS_APPROVAL"]) == "no"
    error_message = "NEEDS_APPROVAL environment variable incorrect"
  }

  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[2].action[0].namespace == "dev-plan"
    error_message = "Input artifacts incorrect"
  }

  # Stage: dev apply
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[3].name == "Apply-dev"
    error_message = "Should be: Apply-dev"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[3].action[0].name == "Apply"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[3].action[0].category == "Build"
    error_message = "Action category incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[3].action[0].owner == "AWS"
    error_message = "Action owner incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[3].action[0].provider == "CodeBuild"
    error_message = "Action provider incorrect"
  }
  assert {
    condition     = length(aws_codepipeline.environment_pipeline.stage[3].action[0].input_artifacts) == 1
    error_message = "Input artifacts incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[3].action[0].input_artifacts[0] == "dev_terraform_plan"
    error_message = "Input artifacts incorrect"
  }
  assert {
    condition     = length(aws_codepipeline.environment_pipeline.stage[3].action[0].output_artifacts) == 0
    error_message = "Output artifacts incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[3].action[0].version == "1"
    error_message = "Action Version incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[3].action[0].configuration.ProjectName == "my-app-my-pipeline-environment-pipeline-apply"
    error_message = "Configuration ProjectName incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[3].action[0].configuration.PrimarySource == "dev_terraform_plan"
    error_message = "Configuration PrimarySource incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.environment_pipeline.stage[3].action[0].configuration.EnvironmentVariables) :
    var.value if try(var.name, "") == "ENVIRONMENT"]) == "dev"
    error_message = "ENVIRONMENT environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.environment_pipeline.stage[3].action[0].configuration.EnvironmentVariables) :
    var.value if try(var.name, "") == "AWS_PROFILE_FOR_COPILOT"]) == "sandbox"
    error_message = "AWS_PROFILE_FOR_COPILOT environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.environment_pipeline.stage[3].action[0].configuration.EnvironmentVariables) :
    var.value if try(var.name, "") == "CURRENT_CODEBUILD_ROLE"]) == "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/my-app-my-pipeline-environment-pipeline-codebuild"
    error_message = "CURRENT_CODEBUILD_ROLE environment variable incorrect"
  }

  # Stage: prod Plan
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[4].name == "Plan-prod"
    error_message = "Should be: Plan-prod"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[4].action[0].name == "Plan"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[4].action[0].category == "Build"
    error_message = "Action category incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[4].action[0].owner == "AWS"
    error_message = "Action owner incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[4].action[0].provider == "CodeBuild"
    error_message = "Action provider incorrect"
  }
  assert {
    condition     = length(aws_codepipeline.environment_pipeline.stage[4].action[0].input_artifacts) == 1
    error_message = "Input artifacts incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[4].action[0].input_artifacts[0] == "build_output"
    error_message = "Input artifacts incorrect"
  }
  assert {
    condition     = length(aws_codepipeline.environment_pipeline.stage[4].action[0].output_artifacts) == 1
    error_message = "Output artifacts incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[4].action[0].output_artifacts[0] == "prod_terraform_plan"
    error_message = "Output artifacts incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[4].action[0].version == "1"
    error_message = "Action Version incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[4].action[0].configuration.ProjectName == "my-app-my-pipeline-environment-pipeline-plan"
    error_message = "Configuration ProjectName incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[4].action[0].configuration.PrimarySource == "build_output"
    error_message = "Configuration PrimarySource incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.environment_pipeline.stage[4].action[0].configuration.EnvironmentVariables) :
    var.value if try(var.name, "") == "ENVIRONMENT"]) == "prod"
    error_message = "ENVIRONMENT environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.environment_pipeline.stage[4].action[0].configuration.EnvironmentVariables) :
    var.value if try(var.name, "") == "NEEDS_APPROVAL"]) == "yes"
    error_message = "NEEDS_APPROVAL environment variable incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[4].action[0].namespace == "prod-plan"
    error_message = "Namespace incorrect"
  }

  # Stage: prod approval
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[5].name == "Approve-prod"
    error_message = "Should be: Approve-prod"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[5].action[0].name == "Approval"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[5].action[0].category == "Approval"
    error_message = "Action category incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[5].action[0].owner == "AWS"
    error_message = "Action owner incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[5].action[0].provider == "Manual"
    error_message = "Action provider incorrect"
  }
  assert {
    condition     = length(aws_codepipeline.environment_pipeline.stage[5].action[0].input_artifacts) == 0
    error_message = "Input artifacts incorrect"
  }
  assert {
    condition     = length(aws_codepipeline.environment_pipeline.stage[5].action[0].output_artifacts) == 0
    error_message = "Output artifacts incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[5].action[0].version == "1"
    error_message = "Action Version incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[5].action[0].configuration.CustomData == "Review Terraform Plan"
    error_message = "Configuration CustomData incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[5].action[0].configuration.ExternalEntityLink == "https://${data.aws_region.current.name}.console.aws.amazon.com/codesuite/codebuild/${data.aws_caller_identity.current.account_id}/projects/my-app-my-pipeline-environment-pipeline-plan/build/#{prod-plan.BUILD_ID}"
    error_message = "Configuration ExternalEntityLink incorrect"
  }

  # Stage: prod apply
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[6].name == "Apply-prod"
    error_message = "Should be: Apply-prod"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[6].action[0].name == "Apply"
    error_message = "Action name incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[6].action[0].category == "Build"
    error_message = "Action category incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[6].action[0].owner == "AWS"
    error_message = "Action owner incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[6].action[0].provider == "CodeBuild"
    error_message = "Action provider incorrect"
  }
  assert {
    condition     = length(aws_codepipeline.environment_pipeline.stage[6].action[0].input_artifacts) == 1
    error_message = "Input artifacts incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[6].action[0].input_artifacts[0] == "prod_terraform_plan"
    error_message = "Input artifacts incorrect"
  }
  assert {
    condition     = length(aws_codepipeline.environment_pipeline.stage[6].action[0].output_artifacts) == 0
    error_message = "Output artifacts incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[6].action[0].version == "1"
    error_message = "Action Version incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[6].action[0].configuration.ProjectName == "my-app-my-pipeline-environment-pipeline-apply"
    error_message = "Configuration ProjectName incorrect"
  }
  assert {
    condition     = aws_codepipeline.environment_pipeline.stage[6].action[0].configuration.PrimarySource == "prod_terraform_plan"
    error_message = "Configuration PrimarySource incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.environment_pipeline.stage[6].action[0].configuration.EnvironmentVariables) :
    var.value if try(var.name, "") == "ENVIRONMENT"]) == "prod"
    error_message = "ENVIRONMENT environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.environment_pipeline.stage[6].action[0].configuration.EnvironmentVariables) :
    var.value if try(var.name, "") == "AWS_PROFILE_FOR_COPILOT"]) == "prod"
    error_message = "AWS_PROFILE_FOR_COPILOT environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.environment_pipeline.stage[6].action[0].configuration.EnvironmentVariables) :
    var.value if try(var.name, "") == "CURRENT_CODEBUILD_ROLE"]) == "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/my-app-my-pipeline-environment-pipeline-codebuild"
    error_message = "CURRENT_CODEBUILD_ROLE environment variable incorrect"
  }
}

run "aws_kms_key_unit_test" {
  command = plan

  assert {
    condition     = aws_kms_key.codebuild_kms_key.description == "KMS Key for my-app-my-pipeline CodeBuild encryption"
    error_message = "Should be: KMS Key for my-app-my-pipeline CodeBuild encryption"
  }

  assert {
    condition     = aws_kms_key.codebuild_kms_key.enable_key_rotation == true
    error_message = "Should be: true"
  }

  assert {
    condition     = jsonencode(aws_kms_key.codebuild_kms_key.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }
}



