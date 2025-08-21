variables {
  application   = "test-app"
  environment   = "test-env"
  database_name = "test-db"
  task = {
    from         = "some-other-env"
    from_account = "000123456789"
    to           = "test-env"
    to_account   = "000123456789"
  }
}

mock_provider "aws" {}

override_data {
  target = data.aws_iam_policy_document.assume_ecs_task_role
  values = {
    json = "{\"Sid\": \"AllowECSAssumeRole\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.allow_task_creation
  values = {
    json = "{\"Sid\": \"AllowPullFromEcr\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.data_load
  values = {
    json = "{\"Sid\": \"AllowReadFromS3\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.pipeline_access
  values = {
    json = "{\"Sid\": \"AllowPipelineAccess\"}"
  }
}

run "data_load_unit_test" {
  command = plan

  assert {
    condition     = local.dump_bucket_name == "test-app-some-other-env-test-db-dump"
    error_message = "Dump bucket name should be: test-app-some-other-env-test-db-dump"
  }

  assert {
    condition     = local.task_name == "test-app-test-env-test-db-load"
    error_message = "Task name incorrect"
  }

  assert {
    condition     = local.dump_task_name == "test-app-some-other-env-test-db-dump"
    error_message = "Dump task name incorrect"
  }

  assert {
    condition     = contains(data.aws_iam_policy_document.allow_task_creation.statement[0].actions, "ecr:GetAuthorizationToken")
    error_message = "Permission not found: ecr:GetAuthorizationToken"
  }

  assert {
    condition     = contains(data.aws_iam_policy_document.allow_task_creation.statement[0].actions, "ecr:BatchCheckLayerAvailability")
    error_message = "Permission not found: ecr:BatchCheckLayerAvailability"
  }

  assert {
    condition     = contains(data.aws_iam_policy_document.allow_task_creation.statement[0].actions, "ecr:GetDownloadUrlForLayer")
    error_message = "Permission not found: ecr:GetDownloadUrlForLayer"
  }

  assert {
    condition     = contains(data.aws_iam_policy_document.allow_task_creation.statement[0].actions, "ecr:BatchGetImage")
    error_message = "Permission not found: ecr:BatchGetImage"
  }

  assert {
    condition     = contains(data.aws_iam_policy_document.allow_task_creation.statement[1].actions, "logs:CreateLogGroup")
    error_message = "Permission not found: logs:CreateLogGroup"
  }

  assert {
    condition     = contains(data.aws_iam_policy_document.allow_task_creation.statement[1].actions, "logs:CreateLogStream")
    error_message = "Permission not found: logs:CreateLogStream"
  }

  assert {
    condition     = contains(data.aws_iam_policy_document.allow_task_creation.statement[1].actions, "logs:PutLogEvents")
    error_message = "Permission not found: logs:PutLogEvents"
  }

  assert {
    condition     = contains(data.aws_iam_policy_document.assume_ecs_task_role.statement[0].actions, "sts:AssumeRole")
    error_message = "Permission not found: sts:AssumeRole"
  }

  assert {
    condition = [
      for el in data.aws_iam_policy_document.assume_ecs_task_role.statement[0].principals :
      true if el.type == "Service" && [
        for identifier in el.identifiers : true if identifier == "ecs-tasks.amazonaws.com"
      ][0] == true
    ][0] == true
    error_message = "Principal identifier should be: 'ecs-tasks.amazonaws.com'"
  }

  assert {
    condition     = aws_iam_role.data_load_task_execution_role.name == "test-app-test-env-test-db-load-exec"
    error_message = "Task execution role name should be: 'test-app-test-env-test-db-load-exec'"
  }

  assert {
    condition     = jsondecode(aws_iam_role.data_load_task_execution_role.assume_role_policy).Sid == "AllowECSAssumeRole"
    error_message = "Statement Sid should be: 'AllowECSAssumeRole'"
  }

  assert {
    condition     = aws_iam_role_policy.allow_task_creation.name == "AllowTaskCreation"
    error_message = "Role policy name should be: 'AllowTaskCreation'"
  }

  assert {
    condition     = aws_iam_role_policy.allow_task_creation.role == "test-app-test-env-test-db-load-exec"
    error_message = "Role name should be: 'test-app-test-env-test-db-load-exec'"
  }

  assert {
    condition     = data.aws_iam_policy_document.data_load.statement[0].sid == "AllowReadFromS3"
    error_message = "Should be 'AllowReadFromS3'"
  }

  assert {
    condition     = length(data.aws_iam_policy_document.data_load.statement) == 3
    error_message = "Should be 3 policy statements"
  }

  assert {
    condition     = length(data.aws_iam_policy_document.data_load.statement[0].actions) == 6
    error_message = "Should be 6 permissions on policy statement"
  }

  assert {
    condition     = data.aws_iam_policy_document.data_load.statement[0].actions == toset(["s3:ListBucket", "s3:GetObject", "s3:GetObjectTagging", "s3:GetObjectVersion", "s3:GetObjectVersionTagging", "s3:DeleteObject"])
    error_message = "Permissions not found"
  }

  assert {
    condition     = data.aws_iam_policy_document.data_load.statement[0].resources == toset(["arn:aws:s3:::test-app-some-other-env-test-db-dump", "arn:aws:s3:::test-app-some-other-env-test-db-dump/*"])
    error_message = "Unexpected resources"
  }

  assert {
    condition     = length(data.aws_iam_policy_document.data_load.statement[1].actions) == 3
    error_message = "Should be 3 permissions on policy statement"
  }

  assert {
    condition     = data.aws_iam_policy_document.data_load.statement[1].actions == toset(["ecs:ListServices", "ecs:DescribeServices", "ecs:UpdateService"])
    error_message = "Permissions not found"
  }

  assert {
    condition     = data.aws_iam_policy_document.data_load.statement[1].resources == toset(["arn:aws:ecs:eu-west-2:${data.aws_caller_identity.current.account_id}:service/default/*", "arn:aws:ecs:eu-west-2:${data.aws_caller_identity.current.account_id}:service/test-app-test-env/*"])
    error_message = "Unexpected resources"
  }

  assert {
    condition     = length(data.aws_iam_policy_document.data_load.statement[2].actions) == 1
    error_message = "Should be 1 permissions on policy statement"
  }

  assert {
    condition     = contains(data.aws_iam_policy_document.data_load.statement[2].actions, "kms:Decrypt")
    error_message = "Permission not found: kms:Decrypt"
  }

  assert {
    condition     = one(data.aws_iam_policy_document.data_load.statement[2].resources) == "arn:aws:kms:eu-west-2:000123456789:key/*"
    error_message = "Unexpected resources"
  }

  assert {
    condition     = aws_iam_role.data_load.name == "test-app-test-env-test-db-load-task"
    error_message = "Name should be test-app-test-env-test-db-load-task"
  }

  assert {
    condition     = jsondecode(aws_iam_role.data_load.assume_role_policy).Sid == "AllowECSAssumeRole"
    error_message = "Assume role policy id should be AllowECSAssumeRole"
  }

  assert {
    condition = (
      aws_iam_role.data_load.tags.application == "test-app" &&
      aws_iam_role.data_load.tags.environment == "test-env" &&
      aws_iam_role.data_load.tags.managed-by == "DBT Platform - Terraform" &&
      aws_iam_role.data_load.tags.copilot-application == "test-app" &&
      aws_iam_role.data_load.tags.copilot-environment == "test-env"
    )
    error_message = "Tags should be as expected"
  }

  assert {
    condition     = aws_iam_role_policy.allow_data_load.name == "AllowDataLoad"
    error_message = "Name should be 'AllowDataLoad'"
  }

  assert {
    condition     = aws_iam_role_policy.allow_data_load.role == "test-app-test-env-test-db-load-task"
    error_message = "Role should be 'test-app-test-env-test-db-load-task'"
  }

  #  aws_iam_role_policy.allow_data_load.policy cannot be tested on a 'plan'

  assert {
    condition     = aws_ecs_task_definition.service.family == "test-app-test-env-test-db-load"
    error_message = "Family should be 'test-app-test-env-test-db-load'"
  }

  assert {
    condition     = aws_ecs_task_definition.service.cpu == "1024"
    error_message = "CPU should be '1024'"
  }

  assert {
    condition     = aws_ecs_task_definition.service.memory == "3072"
    error_message = "CPU should be '3072'"
  }

  assert {
    condition = (
      length(aws_ecs_task_definition.service.requires_compatibilities) == 1 &&
      contains(aws_ecs_task_definition.service.requires_compatibilities, "FARGATE")
    )
    error_message = "Requires compatibilities should be ['FARGATE']"
  }

  # task_role_arn cannot be tested using plan
  # execution_role_arn cannot be tested using plan

  assert {
    condition     = aws_ecs_task_definition.service.network_mode == "awsvpc"
    error_message = "Network modes should be awsvpc"
  }

  assert {
    condition     = aws_ecs_task_definition.service.runtime_platform[0].cpu_architecture == "ARM64"
    error_message = "CPU Arch should be ARM64"
  }

  assert {
    condition     = aws_ecs_task_definition.service.runtime_platform[0].operating_system_family == "LINUX"
    error_message = "OS family should be LINUX"
  }
}

run "cross_account_data_load_unit_test" {
  command = plan

  variables {
    task = {
      from         = "dev"
      from_account = "000123456789"
      to           = "prod"
      to_account   = "123456789000"
    }
  }

  assert {
    condition     = one(data.aws_iam_policy_document.data_load.statement[2].resources) == "arn:aws:kms:eu-west-2:000123456789:key/*"
    error_message = "Unexpected resources"
  }
}

run "pipeline_unit_test" {
  command = plan

  variables {
    task = {
      from : "prod"
      from_account : "123456789000"
      to : "dev"
      to_account : "000123456789"
      pipeline : {}
    }
  }

  assert {
    condition     = local.pipeline_task == true
    error_message = "The pipeline task should be true"
  }
  assert {
    condition     = data.aws_iam_policy_document.assume_ecs_task_role.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.assume_ecs_task_role.statement[1].actions) == "sts:AssumeRole"
    error_message = "Should be: sts:AssumeRole"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.assume_ecs_task_role.statement[1].principals).type == "AWS"
    error_message = "Should be: AWS"
  }
  assert {
    condition     = contains(one(data.aws_iam_policy_document.assume_ecs_task_role.statement[1].principals).identifiers, "arn:aws:iam::000123456789:role/test-db-prod-to-dev-copy-pipeline-codebuild")
    error_message = "Should contain: scheduler.amazonaws.com"
  }
  assert {
    condition     = aws_iam_role_policy.allow_pipeline_access[""].name == "AllowPipelineAccess"
    error_message = "Should be: 'AllowPipelineAccess'"
  }
  assert {
    condition     = aws_iam_role_policy.allow_pipeline_access[""].role == "test-app-test-env-test-db-load-task"
    error_message = "Should be: 'test-app-test-env-test-db-load-task'"
  }
  assert {
    condition     = data.aws_iam_policy_document.pipeline_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = data.aws_iam_policy_document.pipeline_access.statement[0].actions == toset(["iam:ListAccountAliases"])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.pipeline_access.statement[0].resources == toset([
      "*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.pipeline_access.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.pipeline_access.statement[1].actions == toset(["ssm:GetParametersByPath",
      "ssm:GetParameters",
    "ssm:GetParameter"])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.pipeline_access.statement[1].resources == toset([
      "arn:aws:ssm:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:parameter/copilot/*",
      "arn:aws:ssm:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:parameter/platform/applications/*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.pipeline_access.statement[2].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = data.aws_iam_policy_document.pipeline_access.statement[2].actions == toset(["secretsmanager:GetSecretValue"])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.pipeline_access.statement[2].resources == toset([
      "arn:aws:secretsmanager:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:secret:rds*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.pipeline_access.statement[3].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = data.aws_iam_policy_document.pipeline_access.statement[3].actions == toset(["ecs:RunTask"])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.pipeline_access.statement[3].resources == toset([
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:task-definition/*-load:*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.pipeline_access.statement[4].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = data.aws_iam_policy_document.pipeline_access.statement[4].actions == toset(["logs:StartLiveTail"])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.pipeline_access.statement[4].resources == toset([
      "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:/ecs/*-load"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.pipeline_access.statement[5].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = data.aws_iam_policy_document.pipeline_access.statement[5].actions == toset(["iam:PassRole"])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.pipeline_access.statement[5].resources == toset([
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*-load-exec"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.pipeline_access.statement[6].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = data.aws_iam_policy_document.pipeline_access.statement[6].actions == toset(["logs:DescribeLogGroups"])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.pipeline_access.statement[6].resources == toset([
      "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group::log-stream:"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.pipeline_access.statement[7].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = data.aws_iam_policy_document.pipeline_access.statement[7].actions == toset(["elasticache:DescribeCacheEngineVersions"])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.pipeline_access.statement[7].resources == toset([
      "*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.pipeline_access.statement[8].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = data.aws_iam_policy_document.pipeline_access.statement[8].actions == toset(["es:ListVersions", "es:ListElasticsearchVersions"])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.pipeline_access.statement[8].resources == toset([
      "*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.pipeline_access.statement[9].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.pipeline_access.statement[9].actions == toset(["ec2:DescribeVpcs",
      "ec2:DescribeSubnets",
      "ec2:DescribeRouteTables",
    "ec2:DescribeSecurityGroups"])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.pipeline_access.statement[9].resources == toset([
      "*"
    ])
    error_message = "Unexpected resources"
  }
}
