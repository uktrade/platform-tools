variables {
  application   = "test-app"
  environment   = "test-env"
  database_name = "test-db"
  tasks = [
    {
      from         = "staging"
      from_account = "000123456789"
      to           = "dev"
      to_account   = "000123456789"
    }
  ]
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
  target = data.aws_iam_policy_document.pipeline_access
  values = {
    json = "{\"Sid\": \"AllowPipelineAccess\"}"
  }
}

run "data_dump_unit_test" {
  command = plan

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
        ][
        0
      ] == true
      ][
      0
    ] == true
    error_message = "Principal identifier should be: 'ecs-tasks.amazonaws.com'"
  }

  assert {
    condition     = aws_iam_role.data_dump_task_execution_role.name == "test-app-test-env-test-db-dump-exec"
    error_message = "Task execution role name should be: 'test-app-test-env-test-db-dump-exec'"
  }

  assert {
    condition     = jsondecode(aws_iam_role.data_dump_task_execution_role.assume_role_policy).Sid == "AllowECSAssumeRole"
    error_message = "Statement Sid should be: AllowECSAssumeRole"
  }

  assert {
    condition     = aws_iam_role_policy.allow_task_creation.name == "AllowTaskCreation"
    error_message = "Role policy name should be: 'AllowTaskCreation'"
  }

  assert {
    condition     = aws_iam_role_policy.allow_task_creation.role == "test-app-test-env-test-db-dump-exec"
    error_message = "Role name should be: 'test-app-test-env-test-db-dump-exec'"
  }

  assert {
    condition     = data.aws_iam_policy_document.data_dump.statement[0].sid == "AllowWriteToS3"
    error_message = "Should be 'AllowWriteToS3'"
  }

  assert {
    condition     = length(data.aws_iam_policy_document.data_dump.statement) == 2
    error_message = "Should be 1 policy statement"
  }

  assert {
    condition     = contains(data.aws_iam_policy_document.data_dump.statement[0].actions, "s3:ListBucket")
    error_message = "Permission not found: s3:ListBucket"
  }

  assert {
    condition     = contains(data.aws_iam_policy_document.data_dump.statement[0].actions, "s3:PutObject")
    error_message = "Permission not found: s3:PutObject"
  }

  assert {
    condition     = contains(data.aws_iam_policy_document.data_dump.statement[0].actions, "s3:GetObjectTagging")
    error_message = "Permission not found: s3:GetObjectTagging"
  }

  assert {
    condition     = contains(data.aws_iam_policy_document.data_dump.statement[0].actions, "s3:GetObjectVersion")
    error_message = "Permission not found: s3:GetObjectVersion"
  }

  assert {
    condition     = contains(data.aws_iam_policy_document.data_dump.statement[0].actions, "s3:GetObjectVersionTagging")
    error_message = "Permission not found: s3:GetObjectVersionTagging"
  }

  assert {
    condition     = length(data.aws_iam_policy_document.data_dump.statement[0].actions) == 7
    error_message = "Should be 7 permissions on policy statement"
  }

  #  data.aws_iam_policy_document.data_dump.statement[0].resources cannot be tested on a 'plan'

  assert {
    condition     = contains(data.aws_iam_policy_document.data_dump.statement[1].actions, "kms:Encrypt")
    error_message = "Permission not found: kms:Encrypt"
  }

  assert {
    condition     = contains(data.aws_iam_policy_document.data_dump.statement[1].actions, "kms:Decrypt")
    error_message = "Permission not found: kms:Decrypt"
  }

  assert {
    condition     = contains(data.aws_iam_policy_document.data_dump.statement[1].actions, "kms:ReEncrypt*")
    error_message = "Permission not found: kms:ReEncrypt*"
  }

  assert {
    condition     = contains(data.aws_iam_policy_document.data_dump.statement[1].actions, "kms:GenerateDataKey*")
    error_message = "Permission not found: kms:GenerateDataKey*"
  }

  assert {
    condition     = length(data.aws_iam_policy_document.data_dump.statement[1].actions) == 4
    error_message = "Should be 4 permissions on policy statement"
  }

  #  data.aws_iam_policy_document.data_dump.statement[1].resources cannot be tested on a 'plan'

  assert {
    condition     = aws_iam_role.data_dump.name == "test-app-test-env-test-db-dump-task"
    error_message = "Name should be test-app-test-env-test-db-dump-task"
  }

  assert {
    condition     = jsondecode(aws_iam_role.data_dump.assume_role_policy).Sid == "AllowECSAssumeRole"
    error_message = "Assume role policy Sid should be AllowECSAssumeRole"
  }

  assert {
    condition = (
      aws_iam_role.data_dump.tags.application == "test-app" &&
      aws_iam_role.data_dump.tags.environment == "test-env" &&
      aws_iam_role.data_dump.tags.managed-by == "DBT Platform - Terraform" &&
      aws_iam_role.data_dump.tags.copilot-application == "test-app" &&
      aws_iam_role.data_dump.tags.copilot-environment == "test-env"
    )
    error_message = "Tags should be as expected"
  }

  assert {
    condition     = aws_iam_role_policy.allow_data_dump.name == "AllowDataDump"
    error_message = "Name should be 'AllowDataDump'"
  }

  assert {
    condition     = aws_iam_role_policy.allow_data_dump.role == "test-app-test-env-test-db-dump-task"
    error_message = "Role should be 'test-app-test-env-test-db-dump-task'"
  }

  #  aws_iam_role_policy.allow_data_dump.policy cannot be tested on a 'plan'

  assert {
    condition     = aws_ecs_task_definition.service.family == "test-app-test-env-test-db-dump"
    error_message = "Family should be 'test-app-test-env-test-db-dump'"
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

  assert {
    condition     = aws_s3_bucket.data_dump_bucket.bucket == "test-app-test-env-test-db-dump"
    error_message = "Bucket name should be: test-app-test-env-test-db-dump"
  }

  assert {
    condition = (
      aws_s3_bucket.data_dump_bucket.tags.application == "test-app" &&
      aws_s3_bucket.data_dump_bucket.tags.environment == "test-env" &&
      aws_s3_bucket.data_dump_bucket.tags.managed-by == "DBT Platform - Terraform" &&
      aws_s3_bucket.data_dump_bucket.tags.copilot-application == "test-app" &&
      aws_s3_bucket.data_dump_bucket.tags.copilot-environment == "test-env"
    )
    error_message = "Tags should be as expected"
  }

  # data.aws_iam_policy_document.data_dump_bucket_policy.json).Statement[0].Action cannot be tested using plan

  # data.aws_iam_policy_document.data_dump_bucket_policy.json).Statement[0].Effect cannot be tested using plan

  assert {
    condition     = length(data.aws_iam_policy_document.data_dump_bucket_policy.statement[0].condition) == 1
    error_message = "Statement should have a single condition"
  }

  assert {
    condition = [
      for el in data.aws_iam_policy_document.data_dump_bucket_policy.statement[0].condition : true
      if(el.variable == "aws:SecureTransport" && contains(el.values, "false"))
    ] == [true]
    error_message = "Should be denied if not aws:SecureTransport"
  }

  assert {
    condition     = [for el in data.aws_iam_policy_document.data_dump_bucket_policy.statement[1].principals : el.type][0] == "AWS"
    error_message = "Should be: AWS"
  }

  assert {
    condition     = flatten([for el in data.aws_iam_policy_document.data_dump_bucket_policy.statement[1].principals : el.identifiers]) == ["arn:aws:iam::000123456789:role/test-app-dev-test-db-load-task"]
    error_message = "Bucket policy principals incorrect"
  }

  assert {
    condition = data.aws_iam_policy_document.data_dump_bucket_policy.statement[1].actions == toset(["s3:ListBucket",
      "s3:GetObject",
      "s3:GetObjectTagging",
      "s3:GetObjectVersion",
      "s3:GetObjectVersionTagging",
    "s3:DeleteObject"])
    error_message = "Unexpected actions"
  }

  assert {
    condition     = strcontains(aws_kms_key.data_dump_kms_key.policy, "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root") && strcontains(aws_kms_key.data_dump_kms_key.policy, "arn:aws:iam::000123456789:role/test-app-dev-test-db-load-task")
    error_message = "Unexpected KMS key policy principal"
  }

  assert {
    condition     = aws_kms_alias.data_dump_kms_alias.name == "alias/test-app-test-env-test-db-dump"
    error_message = "Kms key alias should be: alias/test-app-test-env-test-db-dump"
  }

  assert {
    condition     = length(aws_s3_bucket_server_side_encryption_configuration.encryption-config.rule) == 1
    error_message = "Server side encryption config with 1 rule should exist for bucket "
  }

  assert {
    condition = [
      for el in aws_s3_bucket_server_side_encryption_configuration.encryption-config.rule :
      el.apply_server_side_encryption_by_default[0].sse_algorithm
    ] == ["aws:kms"]
    error_message = "Server side encryption algorithm should be: aws:kms"
  }

  assert {
    condition = (
      aws_s3_bucket_public_access_block.public_access_block.block_public_acls == true &&
      aws_s3_bucket_public_access_block.public_access_block.block_public_policy == true &&
      aws_s3_bucket_public_access_block.public_access_block.ignore_public_acls == true &&
      aws_s3_bucket_public_access_block.public_access_block.restrict_public_buckets == true
    )
    error_message = "Public access block has expected conditions"
  }
}

run "cross_account_data_dump_unit_test" {
  command = plan

  variables {
    tasks = [
      {
        from         = "dev"
        from_account = "000123456789"
        to           = "hotfix"
        to_account   = "123456789000"
      }
    ]
  }

  assert {
    condition     = [for el in data.aws_iam_policy_document.data_dump_bucket_policy.statement[1].principals : el.type][0] == "AWS"
    error_message = "Should be: AWS"
  }
  assert {
    condition     = flatten([for el in data.aws_iam_policy_document.data_dump_bucket_policy.statement[1].principals : el.identifiers]) == ["arn:aws:iam::123456789000:role/test-app-hotfix-test-db-load-task"]
    error_message = "Bucket policy principals incorrect"
  }
  assert {
    condition = data.aws_iam_policy_document.data_dump_bucket_policy.statement[1].actions == toset(["s3:ListBucket",
      "s3:GetObject",
      "s3:GetObjectTagging",
      "s3:GetObjectVersion",
      "s3:GetObjectVersionTagging",
    "s3:DeleteObject"])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = strcontains(aws_kms_key.data_dump_kms_key.policy, "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root") && strcontains(aws_kms_key.data_dump_kms_key.policy, "arn:aws:iam::123456789000:role/test-app-hotfix-test-db-load-task")
    error_message = "Unexpected KMS key policy principal"
  }
}

run "pipeline_unit_test" {
  command = plan

  variables {
    tasks = [
      {
        from         = "prod"
        from_account = "123456789000"
        to           = "dev"
        to_account   = "000123456789"
        pipeline     = {}
      },
      {
        from         = "prod"
        from_account = "123456789000"
        to           = "staging"
        to_account   = "000123456789"
        pipeline     = {}
      }
    ]
  }

  assert {
    condition     = length(local.pipeline_tasks) == 2
    error_message = "There should be 2 pipeline tasks"
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
    condition     = data.aws_iam_policy_document.assume_ecs_task_role.statement[1].sid == "AllowPipelineAssumeRoleDev"
    error_message = "Statement ID not found: AllowPipelineAssumeRoleDev"
  }
  assert {
    condition     = data.aws_iam_policy_document.assume_ecs_task_role.statement[2].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.assume_ecs_task_role.statement[2].actions) == "sts:AssumeRole"
    error_message = "Should be: sts:AssumeRole"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.assume_ecs_task_role.statement[2].principals).type == "AWS"
    error_message = "Should be: AWS"
  }
  assert {
    condition     = contains(one(data.aws_iam_policy_document.assume_ecs_task_role.statement[2].principals).identifiers, "arn:aws:iam::000123456789:role/test-db-prod-to-staging-copy-pipeline-codebuild")
    error_message = "Should contain: scheduler.amazonaws.com"
  }
  assert {
    condition     = data.aws_iam_policy_document.assume_ecs_task_role.statement[2].sid == "AllowPipelineAssumeRoleStaging"
    error_message = "Statement ID not found: AllowPipelineAssumeRoleStaging"
  }
  assert {
    condition     = aws_iam_role_policy.allow_pipeline_access[""].name == "AllowPipelineAccess"
    error_message = "Should be: 'AllowPipelineAccess'"
  }
  assert {
    condition     = aws_iam_role_policy.allow_pipeline_access[""].role == "test-app-test-env-test-db-dump-task"
    error_message = "Should be: 'test-app-test-env-test-db-dump-task'"
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
      "arn:aws:ssm:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:parameter/copilot/*",
      "arn:aws:ssm:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:parameter/platform/applications/*"
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
      "arn:aws:secretsmanager:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:secret:rds*"
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
      "arn:aws:ecs:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:task-definition/*-dump:*"
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
      "arn:aws:logs:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:log-group:/ecs/*-dump"
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
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*-dump-exec"
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
      "arn:aws:logs:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:log-group::log-stream:"
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
