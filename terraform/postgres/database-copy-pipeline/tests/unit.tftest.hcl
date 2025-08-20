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
  target = data.aws_iam_policy_document.assume_codepipeline_role
  values = {
    json = "{\"Sid\": \"AssumeCodePipeline\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.access_artifact_store
  values = {
    json = "{\"Sid\": \"AccessArtifactStore\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.assume_codebuild_role
  values = {
    json = "{\"Sid\": \"AssumeCodeBuild\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.ssm_access
  values = {
    json = "{\"Sid\": \"SSMAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.assume_database_pipeline_scheduler_role
  values = {
    json = "{\"Sid\": \"AssumePipelineScheduler\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.pipeline_access_for_database_pipeline_scheduler
  values = {
    json = "{\"Sid\": \"SchedulerPipelineAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.assume_account_role
  values = {
    json = "{\"Sid\": \"AllowAssumeAccountRole\"}"
  }
}

variables {
  application   = "test-app"
  environment   = "test-env"
  database_name = "test-db"
  task = {
    from : "prod"
    from_account = "123456789000"
    to : "dev"
    to_account = "000123456789"
    pipeline : {
      schedule : "0 1 * * ? *"
    }
  }
  expected_tags = {
    application         = "test-app"
    environment         = "test-env"
    copilot-application = "test-app"
    copilot-environment = "test-env"
    managed-by          = "DBT Platform - Terraform"
  }
}

run "test_pipeline" {
  command = plan

  assert {
    condition     = aws_codepipeline.database_copy_pipeline.name == "test-db-prod-to-dev-copy-pipeline"
    error_message = "Should be: test-db-prod-to-dev-copy-pipeline"
  }
  assert {
    condition     = tolist(aws_codepipeline.database_copy_pipeline.artifact_store)[0].location == "test-db-prod-to-dev-copy-pipeline-artifact-store"
    error_message = "Should be: test-db-prod-to-dev-copy-pipeline-artifact-store"
  }
  assert {
    condition     = tolist(aws_codepipeline.database_copy_pipeline.artifact_store)[0].type == "S3"
    error_message = "Should be: S3"
  }
  assert {
    condition     = tolist(aws_codepipeline.database_copy_pipeline.artifact_store)[0].encryption_key[0].type == "KMS"
    error_message = "Should be: KMS"
  }
  assert {
    condition     = jsonencode(aws_codepipeline.database_copy_pipeline.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }

  # Source stage
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[0].name == "Source"
    error_message = "Should be: Source"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[0].action[0].name == "GitCheckout"
    error_message = "Should be: Git checkout"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[0].action[0].category == "Source"
    error_message = "Should be: Source"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[0].action[0].owner == "AWS"
    error_message = "Should be: AWS"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[0].action[0].provider == "CodeStarSourceConnection"
    error_message = "Should be: CodeStarSourceConnection"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[0].action[0].version == "1"
    error_message = "Should be: 1"
  }
  assert {
    condition     = one(aws_codepipeline.database_copy_pipeline.stage[0].action[0].output_artifacts) == "project_deployment_source"
    error_message = "Should be: source_output"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[0].action[0].configuration.FullRepositoryId == "uktrade/test-app-deploy"
    error_message = "Should be: uktrade/test-app-deploy"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[0].action[0].configuration.BranchName == "main"
    error_message = "Should be: main"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[0].action[0].configuration.DetectChanges == "false"
    error_message = "Should be: false"
  }

  # Build stage
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[1].name == "Install-Build-Tools"
    error_message = "Should be: Install-Build-Tools"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[1].action[0].name == "InstallTools"
    error_message = "Should be: InstallTools"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[1].action[0].category == "Build"
    error_message = "Should be: Build"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[1].action[0].owner == "AWS"
    error_message = "Should be: AWS"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[1].action[0].provider == "CodeBuild"
    error_message = "Should be: CodeBuild"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[1].action[0].version == "1"
    error_message = "Should be: 1"
  }
  assert {
    condition     = one(aws_codepipeline.database_copy_pipeline.stage[1].action[0].input_artifacts) == "project_deployment_source"
    error_message = "Should be: project_deployment_source"
  }
  assert {
    condition     = one(aws_codepipeline.database_copy_pipeline.stage[1].action[0].output_artifacts) == "build_output"
    error_message = "Should be: build_output"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[1].action[0].configuration.ProjectName == "test-db-prod-to-dev-copy-pipeline-build"
    error_message = "Should be: test-db-prod-to-dev-copy-pipeline-build"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[1].action[0].configuration.PrimarySource == "project_deployment_source"
    error_message = "Should be: project_deployment_source"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.database_copy_pipeline.stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "PIPELINE_NAME"]) == "test-db-prod-to-dev-copy-pipeline"
    error_message = "PIPELINE_NAME environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.database_copy_pipeline.stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "DATABASE_NAME"]) == "test-db"
    error_message = "DATABASE_NAME environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.database_copy_pipeline.stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "FROM_ENVIRONMENT"]) == "prod"
    error_message = "FROM_ENVIRONMENT environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.database_copy_pipeline.stage[1].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "TO_ENVIRONMENT"]) == "dev"
    error_message = "TO_ENVIRONMENT environment variable incorrect"
  }

  # Dump stage
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[2].name == "Database-Dump-prod"
    error_message = "Should be: Database-Dump-prod"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[2].action[0].name == "Dump"
    error_message = "Should be: Dump"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[2].action[0].category == "Build"
    error_message = "Should be: Build"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[2].action[0].owner == "AWS"
    error_message = "Should be: AWS"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[2].action[0].provider == "CodeBuild"
    error_message = "Should be: CodeBuild"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[2].action[0].version == "1"
    error_message = "Should be: 1"
  }
  assert {
    condition     = one(aws_codepipeline.database_copy_pipeline.stage[2].action[0].input_artifacts) == "build_output"
    error_message = "Should be: project_deployment_source"
  }
  assert {
    condition     = flatten(aws_codepipeline.database_copy_pipeline.stage[2].action[0].output_artifacts) == []
    error_message = "Should be: build_output"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[2].action[0].configuration.ProjectName == "test-db-prod-to-dev-copy-pipeline-dump"
    error_message = "Should be: test-db-prod-to-dev-copy-pipeline-dump"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[2].action[0].configuration.PrimarySource == "build_output"
    error_message = "Should be: build_output"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.database_copy_pipeline.stage[2].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "APPLICATION"]) == "test-app"
    error_message = "APPLICATION environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.database_copy_pipeline.stage[2].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "DATABASE_NAME"]) == "test-db"
    error_message = "DATABASE_NAME environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.database_copy_pipeline.stage[2].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "FROM_ENVIRONMENT"]) == "prod"
    error_message = "FROM_ENVIRONMENT environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.database_copy_pipeline.stage[2].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "TO_ENVIRONMENT"]) == "dev"
    error_message = "TO_ENVIRONMENT environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.database_copy_pipeline.stage[2].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "DUMP_ROLE_ARN"]) == "arn:aws:iam::123456789000:role/test-app-prod-test-db-dump-task"
    error_message = "DUMP_ROLE_ARN environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.database_copy_pipeline.stage[2].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "SLACK_REF"]) == "#{slack.SLACK_REF}"
    error_message = "SLACK_REF environment variable incorrect"
  }

  # Load stage
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[3].name == "Database-Load-dev"
    error_message = "Should be: Database-Load-dev"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[3].action[0].name == "Load"
    error_message = "Should be: Load"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[3].action[0].category == "Build"
    error_message = "Should be: Build"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[3].action[0].owner == "AWS"
    error_message = "Should be: AWS"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[3].action[0].provider == "CodeBuild"
    error_message = "Should be: CodeBuild"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[3].action[0].version == "1"
    error_message = "Should be: 1"
  }
  assert {
    condition     = one(aws_codepipeline.database_copy_pipeline.stage[3].action[0].input_artifacts) == "build_output"
    error_message = "Should be: project_deployment_source"
  }
  assert {
    condition     = flatten(aws_codepipeline.database_copy_pipeline.stage[3].action[0].output_artifacts) == []
    error_message = "Should be: build_output"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[3].action[0].configuration.ProjectName == "test-db-prod-to-dev-copy-pipeline-load"
    error_message = "Should be: test-db-prod-to-dev-copy-pipeline-load"
  }
  assert {
    condition     = aws_codepipeline.database_copy_pipeline.stage[3].action[0].configuration.PrimarySource == "build_output"
    error_message = "Should be: build_output"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.database_copy_pipeline.stage[3].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "APPLICATION"]) == "test-app"
    error_message = "APPLICATION environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.database_copy_pipeline.stage[3].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "FROM_ENVIRONMENT"]) == "prod"
    error_message = "FROM_ENVIRONMENT environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.database_copy_pipeline.stage[3].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "TO_ENVIRONMENT"]) == "dev"
    error_message = "TO_ENVIRONMENT environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.database_copy_pipeline.stage[3].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "LOAD_ROLE_ARN"]) == "arn:aws:iam::000123456789:role/test-app-dev-test-db-load-task"
    error_message = "LOAD_ROLE_ARN environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.database_copy_pipeline.stage[3].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "SLACK_REF"]) == "#{slack.SLACK_REF}"
    error_message = "SLACK_REF environment variable incorrect"
  }
}

run "test_codebuild_build" {
  command = plan

  assert {
    condition     = aws_codebuild_project.database_pipeline_build.name == "test-db-prod-to-dev-copy-pipeline-build"
    error_message = "Should be: test-db-prod-to-dev-copy-pipeline-build"
  }
  assert {
    condition     = aws_codebuild_project.database_pipeline_build.description == "Install the build tools for test-db-prod-to-dev-copy-pipeline"
    error_message = "Should be: 'Provisions the my-app application's extensions.'"
  }
  assert {
    condition     = aws_codebuild_project.database_pipeline_build.build_timeout == 5
    error_message = "Should be: 5"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_build.artifacts).type == "CODEPIPELINE"
    error_message = "Should be: 'CODEPIPELINE'"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_build.cache).type == "S3"
    error_message = "Should be: 'S3'"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_build.cache).location == "test-db-prod-to-dev-copy-pipeline-artifact-store"
    error_message = "Should be: 'test-db-prod-to-dev-copy-pipeline-artifact-store'"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_build.environment).compute_type == "BUILD_GENERAL1_SMALL"
    error_message = "Should be: 'BUILD_GENERAL1_SMALL'"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_build.environment).image == "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    error_message = "Should be: 'aws/codebuild/amazonlinux2-x86_64-standard:5.0'"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_build.environment).type == "LINUX_CONTAINER"
    error_message = "Should be: 'LINUX_CONTAINER'"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_build.environment).image_pull_credentials_type == "CODEBUILD"
    error_message = "Should be: 'CODEBUILD'"
  }
  assert {
    condition     = aws_codebuild_project.database_pipeline_build.logs_config[0].cloudwatch_logs[0].group_name == "codebuild/test-db-prod-to-dev-copy-pipeline/log-group"
    error_message = "Should be: 'codebuild/test-db-prod-to-dev-copy-pipeline/log-group'"
  }
  assert {
    condition     = aws_codebuild_project.database_pipeline_build.logs_config[0].cloudwatch_logs[0].stream_name == "codebuild/test-db-prod-to-dev-copy-pipeline/log-stream"
    error_message = "Should be: 'codebuild/test-db-prod-to-dev-copy-pipeline/log-stream'"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_build.source).type == "CODEPIPELINE"
    error_message = "Should be: 'CODEPIPELINE'"
  }
  assert {
    condition     = length(regexall(".*echo \"Installing build tools\".*", aws_codebuild_project.database_pipeline_build.source[0].buildspec)) > 0
    error_message = "Should contain: 'echo \"Installing build tools\"'"
  }
  assert {
    condition     = jsonencode(aws_codebuild_project.database_pipeline_build.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }

  # Cloudwatch config:
  assert {
    condition     = aws_cloudwatch_log_group.database_pipeline_codebuild.name == "codebuild/test-db-prod-to-dev-copy-pipeline/log-group"
    error_message = "Should be: 'codebuild/test-db-prod-to-dev-copy-pipeline/log-group'"
  }
  assert {
    condition     = aws_cloudwatch_log_group.database_pipeline_codebuild.retention_in_days == 90
    error_message = "Should be: 90"
  }
  assert {
    condition     = aws_cloudwatch_log_stream.database_pipeline_codebuild.name == "codebuild/test-db-prod-to-dev-copy-pipeline/log-stream"
    error_message = "Should be: 'codebuild/test-db-prod-to-dev-copy-pipeline/log-stream'"
  }
  assert {
    condition     = aws_cloudwatch_log_stream.database_pipeline_codebuild.log_group_name == "codebuild/test-db-prod-to-dev-copy-pipeline/log-group"
    error_message = "Should be: 'codebuild/test-db-prod-to-dev-copy-pipeline/log-group'"
  }
}

run "test_codebuild_dump" {
  command = plan

  assert {
    condition     = aws_codebuild_project.database_pipeline_dump.name == "test-db-prod-to-dev-copy-pipeline-dump"
    error_message = "Should be: test-db-prod-to-dev-copy-pipeline-dump"
  }
  assert {
    condition     = aws_codebuild_project.database_pipeline_dump.description == "Dump the test-db database from prod"
    error_message = "Should be: 'Dump the test-db database from prod'"
  }
  assert {
    condition     = aws_codebuild_project.database_pipeline_dump.build_timeout == 60
    error_message = "Should be: 5"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_dump.artifacts).type == "CODEPIPELINE"
    error_message = "Should be: 'CODEPIPELINE'"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_dump.cache).type == "S3"
    error_message = "Should be: 'S3'"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_dump.cache).location == "test-db-prod-to-dev-copy-pipeline-artifact-store"
    error_message = "Should be: 'test-db-prod-to-dev-copy-pipeline-artifact-store'"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_dump.environment).compute_type == "BUILD_GENERAL1_SMALL"
    error_message = "Should be: 'BUILD_GENERAL1_SMALL'"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_dump.environment).image == "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    error_message = "Should be: 'aws/codebuild/amazonlinux2-x86_64-standard:5.0'"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_dump.environment).type == "LINUX_CONTAINER"
    error_message = "Should be: 'LINUX_CONTAINER'"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_dump.environment).image_pull_credentials_type == "CODEBUILD"
    error_message = "Should be: 'CODEBUILD'"
  }
  assert {
    condition     = aws_codebuild_project.database_pipeline_dump.logs_config[0].cloudwatch_logs[0].group_name == "codebuild/test-db-prod-to-dev-copy-pipeline/log-group"
    error_message = "Should be: 'codebuild/test-db-prod-to-dev-copy-pipeline/log-group'"
  }
  assert {
    condition     = aws_codebuild_project.database_pipeline_dump.logs_config[0].cloudwatch_logs[0].stream_name == "codebuild/test-db-prod-to-dev-copy-pipeline/log-stream"
    error_message = "Should be: 'codebuild/test-db-prod-to-dev-copy-pipeline/log-stream'"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_dump.source).type == "CODEPIPELINE"
    error_message = "Should be: 'CODEPIPELINE'"
  }
  assert {
    condition     = length(regexall(".*platform-helper database dump.*", aws_codebuild_project.database_pipeline_dump.source[0].buildspec)) > 0
    error_message = "Should contain: 'platform-helper database dump'"
  }
  assert {
    condition     = jsonencode(aws_codebuild_project.database_pipeline_dump.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }
}

run "test_codebuild_load" {
  command = plan

  assert {
    condition     = aws_codebuild_project.database_pipeline_load.name == "test-db-prod-to-dev-copy-pipeline-load"
    error_message = "Should be: test-db-prod-to-dev-copy-pipeline-load"
  }
  assert {
    condition     = aws_codebuild_project.database_pipeline_load.description == "Load the test-db database to dev"
    error_message = "Should be: 'Load the test-db database to dev'"
  }
  assert {
    condition     = aws_codebuild_project.database_pipeline_load.build_timeout == 60
    error_message = "Should be: 5"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_load.artifacts).type == "CODEPIPELINE"
    error_message = "Should be: 'CODEPIPELINE'"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_load.cache).type == "S3"
    error_message = "Should be: 'S3'"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_load.cache).location == "test-db-prod-to-dev-copy-pipeline-artifact-store"
    error_message = "Should be: 'test-db-prod-to-dev-copy-pipeline-artifact-store'"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_load.environment).compute_type == "BUILD_GENERAL1_SMALL"
    error_message = "Should be: 'BUILD_GENERAL1_SMALL'"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_load.environment).image == "aws/codebuild/amazonlinux2-x86_64-standard:5.0"
    error_message = "Should be: 'aws/codebuild/amazonlinux2-x86_64-standard:5.0'"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_load.environment).type == "LINUX_CONTAINER"
    error_message = "Should be: 'LINUX_CONTAINER'"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_load.environment).image_pull_credentials_type == "CODEBUILD"
    error_message = "Should be: 'CODEBUILD'"
  }
  assert {
    condition     = aws_codebuild_project.database_pipeline_load.logs_config[0].cloudwatch_logs[0].group_name == "codebuild/test-db-prod-to-dev-copy-pipeline/log-group"
    error_message = "Should be: 'codebuild/test-db-prod-to-dev-copy-pipeline/log-group'"
  }
  assert {
    condition     = aws_codebuild_project.database_pipeline_load.logs_config[0].cloudwatch_logs[0].stream_name == "codebuild/test-db-prod-to-dev-copy-pipeline/log-stream"
    error_message = "Should be: 'codebuild/test-db-prod-to-dev-copy-pipeline/log-stream'"
  }
  assert {
    condition     = one(aws_codebuild_project.database_pipeline_load.source).type == "CODEPIPELINE"
    error_message = "Should be: 'CODEPIPELINE'"
  }
  assert {
    condition     = length(regexall(".*platform-helper database load.*", aws_codebuild_project.database_pipeline_load.source[0].buildspec)) > 0
    error_message = "Should contain: 'platform-helper database load'"
  }
  assert {
    condition     = jsonencode(aws_codebuild_project.database_pipeline_load.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }
}

run "test_iam" {
  command = plan

  # CodePipeline
  assert {
    condition     = aws_iam_role.database_pipeline_codepipeline.name == "test-db-prod-to-dev-copy-pipeline-codepipeline"
    error_message = "Should be: 'test-db-prod-to-dev-copy-pipeline-codepipeline'"
  }
  assert {
    condition     = aws_iam_role.database_pipeline_codepipeline.assume_role_policy == "{\"Sid\": \"AssumeCodePipeline\"}"
    error_message = "Should be: {\"Sid\": \"AssumeCodePipeline\"}"
  }
  assert {
    condition     = jsonencode(aws_iam_role.database_pipeline_codepipeline.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }
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
  assert {
    condition     = aws_iam_role_policy.artifact_store_access_for_database_pipeline.name == "ArtifactStoreAccess"
    error_message = "Should be: 'ArtifactStoreAccess'"
  }
  assert {
    condition     = aws_iam_role_policy.artifact_store_access_for_database_pipeline.role == "test-db-prod-to-dev-copy-pipeline-codepipeline"
    error_message = "Should be: 'test-db-prod-to-dev-copy-pipeline-codepipeline'"
  }

  # CodeBuild
  assert {
    condition     = aws_iam_role.database_pipeline_codebuild.name == "test-db-prod-to-dev-copy-pipeline-codebuild"
    error_message = "Should be: 'test-db-prod-to-dev-copy-pipeline-codebuild'"
  }
  assert {
    condition     = aws_iam_role.database_pipeline_codebuild.assume_role_policy == "{\"Sid\": \"AssumeCodeBuild\"}"
    error_message = "Should be: {\"Sid\": \"AssumeCodeBuild\"}"
  }
  assert {
    condition     = jsonencode(aws_iam_role.database_pipeline_codebuild.tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }
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
    condition     = aws_iam_role_policy.artifact_store_access_for_codebuild.name == "ArtifactStoreAccess"
    error_message = "Should be: 'ArtifactStoreAccess'"
  }
  assert {
    condition     = aws_iam_role_policy.artifact_store_access_for_codebuild.role == "test-db-prod-to-dev-copy-pipeline-codebuild"
    error_message = "Should be: 'test-db-prod-to-dev-copy-pipeline-codebuild'"
  }
  assert {
    condition     = aws_iam_role_policy.log_access_for_codebuild.name == "LogAccess"
    error_message = "Should be: 'LogAccess'"
  }
  assert {
    condition     = aws_iam_role_policy.log_access_for_codebuild.role == "test-db-prod-to-dev-copy-pipeline-codebuild"
    error_message = "Should be: 'test-db-prod-to-dev-copy-pipeline-codebuild'"
  }
  assert {
    condition     = data.aws_iam_policy_document.log_access_for_codebuild.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = data.aws_iam_policy_document.log_access_for_codebuild.statement[0].actions == toset(["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents", "logs:TagLogGroup"])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = aws_iam_role_policy.ssm_read_access_for_codebuild.name == "SSMAccess"
    error_message = "Should be: 'SSMAccess'"
  }
  assert {
    condition     = aws_iam_role_policy.ssm_read_access_for_codebuild.role == "test-db-prod-to-dev-copy-pipeline-codebuild"
    error_message = "Should be: 'test-db-prod-to-dev-copy-pipeline-codebuild'"
  }
  assert {
    condition     = data.aws_iam_policy_document.ssm_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = data.aws_iam_policy_document.ssm_access.statement[0].actions == toset(["ssm:GetParameter", "ssm:GetParameters"])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.ssm_access.statement[0].resources == toset([
      "arn:aws:ssm:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:parameter/codebuild/slack_*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.ssm_access.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = data.aws_iam_policy_document.ssm_access.statement[1].actions == toset(["ssm:DescribeParameters"])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.ssm_access.statement[1].resources == toset([
      "arn:aws:ssm:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.ssm_access.statement[2].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.ssm_access.statement[2].actions == toset([
      "ssm:PutParameter",
      "ssm:GetParameter",
      "ssm:GetParameters",
      "ssm:GetParametersByPath",
      "ssm:DeleteParameter",
      "ssm:AddTagsToResource",
      "ssm:ListTagsForResource"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.ssm_access.statement[2].resources == toset([
      "arn:aws:ssm:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:parameter/copilot/test-app/*/secrets/*",
      "arn:aws:ssm:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:parameter/copilot/applications/test-app",
      "arn:aws:ssm:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:parameter/copilot/applications/test-app/*",
      "arn:aws:ssm:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:parameter/platform/applications/test-app/environments/*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = aws_iam_role_policy.assume_account_role_access_for_codebuild.name == "AssumeAccountRole"
    error_message = "Should be: 'AssumeAccountRole'"
  }
  assert {
    condition     = aws_iam_role_policy.assume_account_role_access_for_codebuild.role == "test-db-prod-to-dev-copy-pipeline-codebuild"
    error_message = "Should be: 'test-db-prod-to-dev-copy-pipeline-codebuild'"
  }
  assert {
    condition     = data.aws_iam_policy_document.assume_account_role.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = data.aws_iam_policy_document.assume_account_role.statement[0].actions == toset(["sts:AssumeRole"])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.assume_account_role.statement[0].resources == toset([
      "arn:aws:iam::123456789000:role/test-app-prod-test-db-dump-task",
      "arn:aws:iam::000123456789:role/test-app-dev-test-db-load-task"
    ])
    error_message = "Unexpected resources"
  }
}

run "test_same_account_iam" {
  command = plan

  variables {
    task = {
      from : "staging"
      from_account = "000123456789"
      to : "dev"
      to_account = "000123456789"
      pipeline : {}
    }
  }

  assert {
    condition = one([for var in jsondecode(aws_codepipeline.database_copy_pipeline.stage[2].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "DUMP_ROLE_ARN"]) == "arn:aws:iam::000123456789:role/test-app-staging-test-db-dump-task"
    error_message = "DUMP_ROLE_ARN environment variable incorrect"
  }
  assert {
    condition = one([for var in jsondecode(aws_codepipeline.database_copy_pipeline.stage[3].action[0].configuration.EnvironmentVariables) :
    var.value if var.name == "LOAD_ROLE_ARN"]) == "arn:aws:iam::000123456789:role/test-app-dev-test-db-load-task"
    error_message = "LOAD_ROLE_ARN environment variable incorrect"
  }
  assert {
    condition = data.aws_iam_policy_document.assume_account_role.statement[0].resources == toset([
      "arn:aws:iam::000123456789:role/test-app-staging-test-db-dump-task",
      "arn:aws:iam::000123456789:role/test-app-dev-test-db-load-task"
    ])
    error_message = "Unexpected resources"
  }
}

run "test_artifact_store" {
  command = plan

  assert {
    condition     = aws_s3_bucket.artifact_store.bucket == "test-db-prod-to-dev-copy-pipeline-artifact-store"
    error_message = "Should be: test-db-prod-to-dev-copy-pipeline-artifact-store"
  }
  assert {
    condition     = aws_kms_alias.artifact_store_kms_alias.name == "alias/test-db-prod-to-dev-copy-pipeline-artifact-store-key"
    error_message = "Should be: alias/test-db-prod-to-dev-copy-pipeline-artifact-store-key"
  }
  assert {
    condition     = [for el in data.aws_iam_policy_document.artifact_store_bucket_policy.statement[0].condition : true if el.variable == "aws:SecureTransport"][0] == true
    error_message = "Should be: aws:SecureTransport"
  }
  assert {
    condition     = data.aws_iam_policy_document.artifact_store_bucket_policy.statement[0].effect == "Deny"
    error_message = "Should be: Deny"
  }
  assert {
    condition     = [for el in data.aws_iam_policy_document.artifact_store_bucket_policy.statement[0].actions : true if el == "s3:*"][0] == true
    error_message = "Should be: s3:*"
  }
}

run "test_pipeline_schedule" {
  command = plan

  assert {
    condition     = aws_scheduler_schedule.database_pipeline_schedule[""].name == "test-db-prod-to-dev-copy-pipeline"
    error_message = "Should be: test-db-prod-to-dev-copy-pipeline"
  }
  assert {
    condition     = aws_scheduler_schedule.database_pipeline_schedule[""].schedule_expression == "cron(0 1 * * ? *)"
    error_message = "Should be: cron(0 1 * * ? *)"
  }
  assert {
    condition     = aws_iam_role.database_pipeline_schedule[""].name == "test-db-prod-to-dev-copy-pipeline-scheduler"
    error_message = "Should be: 'test-db-prod-to-dev-copy-pipeline-scheduler'"
  }
  assert {
    condition     = aws_iam_role.database_pipeline_schedule[""].assume_role_policy == "{\"Sid\": \"AssumePipelineScheduler\"}"
    error_message = "Should be: {\"Sid\": \"AssumePipelineScheduler\"}"
  }
  assert {
    condition     = jsonencode(aws_iam_role.database_pipeline_schedule[""].tags) == jsonencode(var.expected_tags)
    error_message = "Should be: ${jsonencode(var.expected_tags)}"
  }
  assert {
    condition     = data.aws_iam_policy_document.assume_database_pipeline_scheduler_role.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.assume_database_pipeline_scheduler_role.statement[0].actions) == "sts:AssumeRole"
    error_message = "Should be: sts:AssumeRole"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.assume_database_pipeline_scheduler_role.statement[0].principals).type == "Service"
    error_message = "Should be: Service"
  }
  assert {
    condition     = contains(one(data.aws_iam_policy_document.assume_database_pipeline_scheduler_role.statement[0].principals).identifiers, "scheduler.amazonaws.com")
    error_message = "Should contain: scheduler.amazonaws.com"
  }
  assert {
    condition     = aws_iam_role_policy.database_pipeline_schedule[""].name == "SchedulerAccess"
    error_message = "Should be: 'SchedulerAccess'"
  }
  assert {
    condition     = aws_iam_role_policy.database_pipeline_schedule[""].role == "test-db-prod-to-dev-copy-pipeline-scheduler"
    error_message = "Should be: 'test-db-prod-to-dev-copy-pipeline-scheduler'"
  }
  assert {
    condition     = data.aws_iam_policy_document.pipeline_access_for_database_pipeline_scheduler.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = data.aws_iam_policy_document.pipeline_access_for_database_pipeline_scheduler.statement[0].actions == toset(["codepipeline:StartPipelineExecution"])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.pipeline_access_for_database_pipeline_scheduler.statement[0].resources == toset([
      "arn:aws:codepipeline:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:test-db-prod-to-dev-copy-pipeline"
    ])
    error_message = "Unexpected resources"
  }
}

run "test_pipeline_no_schedule" {
  command = plan

  variables {
    task = {
      from : "prod"
      from_account = "123456789000"
      to : "dev"
      to_account = "000123456789"
      pipeline : {}
    }
  }

  assert {
    condition     = aws_scheduler_schedule.database_pipeline_schedule == {}
    error_message = "No schedule should be created"
  }
}
