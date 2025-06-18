mock_provider "aws" {}

variables {
  application = "test-application"
  environment = "test-env"
  env_config = {
    "*" = {
      accounts = {
        deploy = {
          name = "sandbox"
          id   = "000123456789"
        }
        dns = {
          name = "dev"
          id   = "123456"
        }
      }
      vpc : "test-vpc"
    },
    "test-env" = {
      accounts = {
        deploy = {
          name = "sandbox"
          id   = "000123456789"
        }
        dns = {
          name = "dev"
          id   = "123456"
        }
      }
      vpc : "test-vpc"
    }
  }
  tags = {
    application         = "test-application"
    environment         = "test-env"
    managed-by          = "DBT Platform - Terraform"
    copilot-application = "test-application"
    copilot-environment = "test-env"
  }
}

override_data {
  target = data.aws_iam_policy_document.assume_codebase_pipeline
  values = {
    json = "{\"Sid\": \"CodeBaseDeployAssume\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.ecr_access
  values = {
    json = "{\"Sid\": \"ECRAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.artifact_store_access
  values = {
    json = "{\"Sid\": \"ArtifactStoreAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.ecs_deploy_access
  values = {
    json = "{\"Sid\": \"ECSDeployAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.cloudformation_access
  values = {
    json = "{\"Sid\": \"CloudFormationAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.assume_environment_pipeline
  values = {
    json = "{\"Sid\": \"AssumeEnvironmentPipeline\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.terraform_state_access
  values = {
    json = "{\"Sid\": \"TerraformStateAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.vpc_access
  values = {
    json = "{\"Sid\": \"VPCAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.alb_cdn_cert_access
  values = {
    json = "{\"Sid\": \"ALBAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.ssm_access
  values = {
    json = "{\"Sid\": \"SSMAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.logs_access
  values = {
    json = "{\"Sid\": \"LogsAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.kms_key_access
  values = {
    json = "{\"Sid\": \"KMSAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.redis_access
  values = {
    json = "{\"Sid\": \"RedisAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.postgres_access
  values = {
    json = "{\"Sid\": \"PostgresAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.s3_access
  values = {
    json = "{\"Sid\": \"S3Access\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.opensearch_access
  values = {
    json = "{\"Sid\": \"OpensearchAccess\"}"
  }
}

override_data {
  target = data.aws_iam_policy_document.iam_access
  values = {
    json = "{\"Sid\": \"IAMAccess\"}"
  }
}

override_data {
  target = data.aws_ssm_parameter.central_log_group_parameter
  values = {
    value = "{\"prod\":\"arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_prod\", \"dev\":\"arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_dev\"}"
  }
}

run "codebase_deploy_iam_test" {
  command = plan

  assert {
    condition     = aws_iam_role.codebase_pipeline_deploy.name == "test-application-test-env-codebase-pipeline-deploy"
    error_message = "Should be: 'test-application-test-env-codebase-pipeline-deploy'"
  }
  assert {
    condition     = aws_iam_role.codebase_pipeline_deploy.assume_role_policy == "{\"Sid\": \"CodeBaseDeployAssume\"}"
    error_message = "Should be: {\"Sid\": \"CodeBaseDeployAssume\"}"
  }
  assert {
    condition     = data.aws_iam_policy_document.assume_codebase_pipeline.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.assume_codebase_pipeline.statement[0].actions) == "sts:AssumeRole"
    error_message = "Should be: sts:AssumeRole"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.assume_codebase_pipeline.statement[0].principals).type == "AWS"
    error_message = "Should be: AWS"
  }
  assert {
    condition     = contains(one(data.aws_iam_policy_document.assume_codebase_pipeline.statement[0].principals).identifiers, "arn:aws:iam::000123456789:root")
    error_message = "Should contain: arn:aws:iam::000123456789:root"
  }
  assert {
    condition     = [for el in data.aws_iam_policy_document.assume_codebase_pipeline.statement[0].condition : el.test][0] == "ArnLike"
    error_message = "Should be: ArnLike"
  }
  assert {
    condition     = [for el in data.aws_iam_policy_document.assume_codebase_pipeline.statement[0].condition : el.variable][0] == "aws:PrincipalArn"
    error_message = "Should be: aws:PrincipalArn"
  }
  assert {
    condition = flatten([for el in data.aws_iam_policy_document.assume_codebase_pipeline.statement[0].condition : el.values][0]) == [
      "arn:aws:iam::000123456789:role/test-application-*-codebase-pipeline",
      "arn:aws:iam::000123456789:role/test-application-*-codebase-pipeline-*",
      "arn:aws:iam::000123456789:role/test-application-*-codebase-*"
    ]
    error_message = "Unexpected condition values"
  }
  assert {
    condition     = jsonencode(aws_iam_role.codebase_pipeline_deploy.tags) == jsonencode(var.tags)
    error_message = "Should be: ${jsonencode(var.tags)}"
  }
  assert {
    condition     = aws_iam_role_policy.ecr_access.name == "ecr-access"
    error_message = "Should be: 'ecr-access'"
  }
  assert {
    condition     = aws_iam_role_policy.ecr_access.role == "test-application-test-env-codebase-pipeline-deploy"
    error_message = "Should be: 'test-application-test-env-codebase-pipeline-deploy'"
  }
  assert {
    condition     = aws_iam_role_policy.ecr_access.policy == "{\"Sid\": \"ECRAccess\"}"
    error_message = "Should be: {\"Sid\": \"ECRAccess\"}"
  }
  assert {
    condition     = data.aws_iam_policy_document.ecr_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.ecr_access.statement[0].actions) == "ecr:DescribeImages"
    error_message = "Unexpected actions"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.ecr_access.statement[0].resources) == "arn:aws:ecr:${data.aws_region.current.name}:000123456789:repository/test-application/*"
    error_message = "Unexpected resources"
  }
  assert {
    condition     = aws_iam_role_policy.artifact_store_access.name == "artifact-store-access"
    error_message = "Should be: 'artifact-store-access'"
  }
  assert {
    condition     = aws_iam_role_policy.artifact_store_access.role == "test-application-test-env-codebase-pipeline-deploy"
    error_message = "Should be: 'test-application-test-env-codebase-pipeline-deploy'"
  }
  assert {
    condition     = aws_iam_role_policy.artifact_store_access.policy == "{\"Sid\": \"ArtifactStoreAccess\"}"
    error_message = "Should be: {\"Sid\": \"ArtifactStoreAccess\"}"
  }
  assert {
    condition     = data.aws_iam_policy_document.artifact_store_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.artifact_store_access.statement[0].actions == toset([
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:GetBucketVersioning",
      "s3:PutObjectAcl",
      "s3:PutObject",
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = data.aws_iam_policy_document.artifact_store_access.statement[0].resources == toset(["arn:aws:s3:::test-application-*-cb-arts", "arn:aws:s3:::test-application-*-cb-arts/*"])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.artifact_store_access.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.artifact_store_access.statement[1].actions == toset([
      "codebuild:BatchGetBuilds",
      "codebuild:StartBuild",
      "codebuild:StopBuild"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.artifact_store_access.statement[1].resources) == "*"
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.artifact_store_access.statement[2].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.artifact_store_access.statement[2].actions == toset([
      "kms:GenerateDataKey",
      "kms:Decrypt"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.artifact_store_access.statement[2].resources) == "arn:aws:kms:${data.aws_region.current.name}:000123456789:key/*"
    error_message = "Unexpected resources"
  }
  assert {
    condition     = aws_iam_role_policy.ecs_deploy_access.name == "ecs-deploy-access"
    error_message = "Should be: 'ecs-deploy-access'"
  }
  assert {
    condition     = aws_iam_role_policy.ecs_deploy_access.role == "test-application-test-env-codebase-pipeline-deploy"
    error_message = "Should be: 'test-application-test-env-codebase-pipeline-deploy'"
  }
  assert {
    condition     = aws_iam_role_policy.ecs_deploy_access.policy == "{\"Sid\": \"ECSDeployAccess\"}"
    error_message = "Should be: {\"Sid\": \"ECSDeployAccess\"}"
  }
  assert {
    condition     = data.aws_iam_policy_document.ecs_deploy_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.ecs_deploy_access.statement[0].actions == toset([
      "ecs:UpdateService",
      "ecs:DescribeServices",
      "ecs:TagResource",
      "ecs:ListServices"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.ecs_deploy_access.statement[0].resources == toset([
      "arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:cluster/test-application-test-env",
      "arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:service/test-application-test-env/*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.ecs_deploy_access.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.ecs_deploy_access.statement[1].actions == toset([
      "ecs:DescribeTasks",
      "ecs:TagResource"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.ecs_deploy_access.statement[1].resources == toset([
      "arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:cluster/test-application-test-env",
      "arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:task/test-application-test-env/*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.ecs_deploy_access.statement[2].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.ecs_deploy_access.statement[2].actions == toset([
      "ecs:RunTask",
      "ecs:TagResource"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.ecs_deploy_access.statement[2].resources) == "arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:task-definition/test-application-test-env-*:*"
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.ecs_deploy_access.statement[3].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.ecs_deploy_access.statement[3].actions) == "ecs:ListTasks"
    error_message = "Unexpected actions"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.ecs_deploy_access.statement[3].resources) == "arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:container-instance/test-application-test-env/*"
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.ecs_deploy_access.statement[4].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.ecs_deploy_access.statement[4].actions == toset([
      "ecs:DescribeTaskDefinition",
      "ecs:RegisterTaskDefinition"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.ecs_deploy_access.statement[4].resources) == "*"
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.ecs_deploy_access.statement[5].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.ecs_deploy_access.statement[5].actions) == "iam:PassRole"
    error_message = "Unexpected actions"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.ecs_deploy_access.statement[5].resources) == "*"
    error_message = "Unexpected resources"
  }
  assert {
    condition     = [for el in data.aws_iam_policy_document.ecs_deploy_access.statement[5].condition : el.test][0] == "StringLike"
    error_message = "Should be: StringLike"
  }
  assert {
    condition     = [for el in data.aws_iam_policy_document.ecs_deploy_access.statement[5].condition : one(el.values)][0] == "ecs-tasks.amazonaws.com"
    error_message = "Should be: ecs-tasks.amazonaws.com"
  }
  assert {
    condition     = [for el in data.aws_iam_policy_document.ecs_deploy_access.statement[5].condition : el.variable][0] == "iam:PassedToService"
    error_message = "Should be: iam:PassedToService"
  }
  assert {
    condition     = data.aws_iam_policy_document.ecs_deploy_access.statement[6].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.ecs_deploy_access.statement[6].actions == toset([
      "ecs:ListServiceDeployments"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.ecs_deploy_access.statement[6].resources) == "arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:service/test-application-test-env/*"
    error_message = "Unexpected resources"
  }
  assert {
    condition     = aws_iam_role_policy.cloudformation_access.name == "cloudformation-access"
    error_message = "Should be: 'cloudformation-access'"
  }
  assert {
    condition     = aws_iam_role_policy.cloudformation_access.role == "test-application-test-env-codebase-pipeline-deploy"
    error_message = "Should be: 'test-application-test-env-codebase-pipeline-deploy'"
  }
  assert {
    condition     = aws_iam_role_policy.cloudformation_access.policy == "{\"Sid\": \"CloudFormationAccess\"}"
    error_message = "Should be: {\"Sid\": \"CloudFormationAccess\"}"
  }
  assert {
    condition     = data.aws_iam_policy_document.cloudformation_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.cloudformation_access.statement[0].actions == toset([
      "cloudformation:GetTemplate"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.cloudformation_access.statement[0].resources == toset([
      "arn:aws:cloudformation:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:stack/test-application-test-env-*"
    ])
    error_message = "Unexpected resources"
  }
}

run "environment_deploy_iam_role_test" {
  command = plan

  assert {
    condition     = aws_iam_role.environment_pipeline_deploy.name == "test-application-test-env-environment-pipeline-deploy"
    error_message = "Should be: 'test-application-test-env-environment-pipeline-deploy'"
  }
  assert {
    condition     = aws_iam_role.environment_pipeline_deploy.assume_role_policy == "{\"Sid\": \"AssumeEnvironmentPipeline\"}"
    error_message = "Should be: {\"Sid\": \"AssumeEnvironmentPipeline\"}"
  }
  assert {
    condition     = data.aws_iam_policy_document.assume_environment_pipeline.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.assume_environment_pipeline.statement[0].actions) == "sts:AssumeRole"
    error_message = "Should be: sts:AssumeRole"
  }
  assert {
    condition     = one(data.aws_iam_policy_document.assume_environment_pipeline.statement[0].principals).type == "AWS"
    error_message = "Should be: AWS"
  }
  assert {
    condition     = contains(one(data.aws_iam_policy_document.assume_environment_pipeline.statement[0].principals).identifiers, "arn:aws:iam::000123456789:root")
    error_message = "Should contain: arn:aws:iam::000123456789:root"
  }
  assert {
    condition     = [for el in data.aws_iam_policy_document.assume_environment_pipeline.statement[0].condition : el.test][0] == "ArnLike"
    error_message = "Should be: ArnLike"
  }
  assert {
    condition     = [for el in data.aws_iam_policy_document.assume_environment_pipeline.statement[0].condition : el.variable][0] == "aws:PrincipalArn"
    error_message = "Should be: aws:PrincipalArn"
  }
  assert {
    condition = flatten([for el in data.aws_iam_policy_document.assume_environment_pipeline.statement[0].condition : el.values][0]) == [
      "arn:aws:iam::000123456789:role/test-application-*-environment-pipeline-codebuild"
    ]
    error_message = "Unexpected condition values"
  }
  assert {
    condition     = jsonencode(aws_iam_role.codebase_pipeline_deploy.tags) == jsonencode(var.tags)
    error_message = "Should be: ${jsonencode(var.tags)}"
  }
}

run "environment_deploy_iam_terraform_state_test" {
  command = plan

  assert {
    condition     = aws_iam_role_policy.terraform_state_access.role == "test-application-test-env-environment-pipeline-deploy"
    error_message = "Should be: 'test-application-test-env-environment-pipeline-deploy'"
  }
  assert {
    condition     = aws_iam_role_policy.terraform_state_access.name == "terraform-state-access"
    error_message = "Should be: 'terraform-state-access'"
  }
  assert {
    condition     = aws_iam_role_policy.terraform_state_access.policy == "{\"Sid\": \"TerraformStateAccess\"}"
    error_message = "Should be: {\"Sid\": \"TerraformStateAccess\"}"
  }
  assert {
    condition     = data.aws_iam_policy_document.terraform_state_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.terraform_state_access.statement[0].actions == toset([
      "s3:ListBucket",
      "s3:GetObject",
      "s3:PutObject"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = data.aws_iam_policy_document.terraform_state_access.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.terraform_state_access.statement[1].actions == toset([
      "kms:ListKeys",
      "kms:Decrypt",
      "kms:GenerateDataKey"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = data.aws_iam_policy_document.terraform_state_access.statement[2].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.terraform_state_access.statement[2].actions == toset([
      "dynamodb:DescribeTable",
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:DeleteItem"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.terraform_state_access.statement[2].resources == toset([
      "arn:aws:dynamodb:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:table/terraform-platform-lockdb-sandbox"
    ])
    error_message = "Unexpected resources"
  }
}

run "environment_deploy_iam_vpc_access" {
  command = plan

  assert {
    condition     = aws_iam_role_policy.vpc_access.role == "test-application-test-env-environment-pipeline-deploy"
    error_message = "Should be: 'test-application-test-env-environment-pipeline-deploy'"
  }
  assert {
    condition     = aws_iam_role_policy.vpc_access.name == "vpc-access"
    error_message = "Should be: 'vpc-access'"
  }
  assert {
    condition     = aws_iam_role_policy.vpc_access.policy == "{\"Sid\": \"VPCAccess\"}"
    error_message = "Should be: {\"Sid\": \"VPCAccess\"}"
  }
  assert {
    condition     = data.aws_iam_policy_document.vpc_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.vpc_access.statement[0].actions == toset([
      "ec2:DescribeVpcs",
      "ec2:DescribeSubnets",
      "ec2:DescribeSecurityGroups",
      "ec2:DescribeNetworkInterfaces"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.vpc_access.statement[0].resources == toset([
      "*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.vpc_access.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.vpc_access.statement[1].actions == toset([
      "ec2:DescribeVpcAttribute",
      "ec2:CreateSecurityGroup"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.vpc_access.statement[1].resources == toset([
      "arn:aws:ec2:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:vpc/*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.vpc_access.statement[2].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.vpc_access.statement[2].actions == toset([
      "ec2:CreateSecurityGroup",
      "ec2:CreateTags",
      "ec2:RevokeSecurityGroupEgress",
      "ec2:RevokeSecurityGroupIngress",
      "ec2:DeleteSecurityGroup",
      "ec2:AuthorizeSecurityGroupIngress",
      "ec2:AuthorizeSecurityGroupEgress"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.vpc_access.statement[2].resources == toset([
      "arn:aws:ec2:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:security-group/*"
    ])
    error_message = "Unexpected resources"
  }
}

run "environment_deploy_iam_ssm_access" {
  command = plan

  assert {
    condition     = aws_iam_role_policy.ssm_access.role == "test-application-test-env-environment-pipeline-deploy"
    error_message = "Should be: 'test-application-test-env-environment-pipeline-deploy'"
  }
  assert {
    condition     = aws_iam_role_policy.ssm_access.name == "ssm-access"
    error_message = "Should be: 'ssm-access'"
  }
  assert {
    condition     = aws_iam_role_policy.ssm_access.policy == "{\"Sid\": \"SSMAccess\"}"
    error_message = "Should be: {\"Sid\": \"SSMAccess\"}"
  }
  assert {
    condition     = data.aws_iam_policy_document.ssm_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.ssm_access.statement[0].actions == toset([
      "ssm:DescribeParameters"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.ssm_access.statement[0].resources == toset([
      "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.ssm_access.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.ssm_access.statement[1].actions == toset([
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
    condition = data.aws_iam_policy_document.ssm_access.statement[1].resources == toset([
      "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/copilot/test-application/*/secrets/*",
      "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/copilot/applications/test-application",
      "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/copilot/applications/test-application/*",
      "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/***"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.ssm_access.statement[2].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.ssm_access.statement[2].actions == toset([
      "ssm:GetParameter",
      "ssm:GetParameters"
    ])
    error_message = "Unexpected actions"
  }
}

run "environment_deploy_iam_logs_access" {
  command = plan

  assert {
    condition     = aws_iam_role_policy.logs_access.role == "test-application-test-env-environment-pipeline-deploy"
    error_message = "Should be: 'test-application-test-env-environment-pipeline-deploy'"
  }
  assert {
    condition     = aws_iam_role_policy.logs_access.name == "logs-access"
    error_message = "Should be: 'logs-access'"
  }
  assert {
    condition     = aws_iam_role_policy.logs_access.policy == "{\"Sid\": \"LogsAccess\"}"
    error_message = "Should be: {\"Sid\": \"LogsAccess\"}"
  }
  assert {
    condition     = data.aws_iam_policy_document.logs_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.logs_access.statement[0].actions == toset([
      "cloudwatch:GetDashboard",
      "cloudwatch:PutDashboard",
      "cloudwatch:DeleteDashboards"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.logs_access.statement[0].resources == toset([
      "arn:aws:cloudwatch::${data.aws_caller_identity.current.account_id}:dashboard/test-application-test-env-compute"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.logs_access.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.logs_access.statement[1].actions == toset([
      "resource-groups:GetGroup",
      "resource-groups:CreateGroup",
      "resource-groups:Tag",
      "resource-groups:GetGroupQuery",
      "resource-groups:GetGroupConfiguration",
      "resource-groups:GetTags",
      "resource-groups:DeleteGroup"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.logs_access.statement[1].resources == toset([
      "arn:aws:resource-groups:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:group/test-application-test-env-application-insights-resources"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.logs_access.statement[2].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.logs_access.statement[2].actions == toset([
      "applicationinsights:CreateApplication",
      "applicationinsights:TagResource",
      "applicationinsights:DescribeApplication",
      "applicationinsights:ListTagsForResource",
      "applicationinsights:DeleteApplication"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.logs_access.statement[2].resources == toset([
      "arn:aws:applicationinsights:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:application/resource-group/test-application-test-env-application-insights-resources"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.logs_access.statement[3].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.logs_access.statement[3].actions == toset([
      "logs:DescribeResourcePolicies",
      "logs:PutResourcePolicy",
      "logs:DeleteResourcePolicy",
      "logs:DescribeLogGroups"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.logs_access.statement[3].resources == toset([
      "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group::log-stream:"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.logs_access.statement[4].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.logs_access.statement[4].actions == toset([
      "logs:PutSubscriptionFilter"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.logs_access.statement[4].resources == toset([
      "arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_dev",
      "arn:aws:logs:eu-west-2:123456789987:destination:central_log_groups_prod"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.logs_access.statement[5].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.logs_access.statement[5].actions == toset([
      "logs:PutRetentionPolicy",
      "logs:ListTagsLogGroup",
      "logs:ListTagsForResource",
      "logs:DeleteLogGroup",
      "logs:CreateLogGroup",
      "logs:PutSubscriptionFilter",
      "logs:DescribeSubscriptionFilters",
      "logs:DeleteSubscriptionFilter",
      "logs:TagResource",
      "logs:AssociateKmsKey",
      "logs:DescribeLogStreams",
      "logs:DeleteLogStream"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.logs_access.statement[5].resources == toset([
      "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/opensearch/*",
      "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/rds/*",
      "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/elasticache/*",
      "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:codebuild/*",
      "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/conduit/*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.logs_access.statement[6].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.logs_access.statement[6].actions == toset([
      "cloudformation:ListExports"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = data.aws_iam_policy_document.logs_access.statement[6].resources == toset(["*"])
    error_message = "Unexpected resources"
  }
}

run "environment_deploy_iam_kms_key_access" {
  command = plan

  assert {
    condition     = aws_iam_role_policy.kms_key_access.role == "test-application-test-env-environment-pipeline-deploy"
    error_message = "Should be: 'test-application-test-env-environment-pipeline-deploy'"
  }
  assert {
    condition     = aws_iam_role_policy.kms_key_access.name == "kms-key-access"
    error_message = "Should be: 'kms-key-access'"
  }
  assert {
    condition     = aws_iam_role_policy.kms_key_access.policy == "{\"Sid\": \"KMSAccess\"}"
    error_message = "Should be: {\"Sid\": \"KMSAccess\"}"
  }
  assert {
    condition     = data.aws_iam_policy_document.kms_key_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.kms_key_access.statement[0].actions == toset([
      "kms:CreateKey",
      "kms:ListAliases"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition     = data.aws_iam_policy_document.kms_key_access.statement[0].resources == toset(["*"])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.kms_key_access.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.kms_key_access.statement[1].actions == toset([
      "kms:*"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.kms_key_access.statement[1].resources == toset([
      "arn:aws:kms:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:key/*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.kms_key_access.statement[2].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.kms_key_access.statement[2].actions == toset([
      "kms:CreateAlias",
      "kms:DeleteAlias"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.kms_key_access.statement[2].resources == toset([
      "arn:aws:kms:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:alias/test-application-*"
    ])
    error_message = "Unexpected resources"
  }
}

run "environment_deploy_iam_iam_access" {
  command = plan

  assert {
    condition     = aws_iam_role_policy.iam_access.role == "test-application-test-env-environment-pipeline-deploy"
    error_message = "Should be: 'test-application-test-env-environment-pipeline-deploy'"
  }
  assert {
    condition     = aws_iam_role_policy.iam_access.name == "iam-access"
    error_message = "Should be: 'iam-access'"
  }
  assert {
    condition     = aws_iam_role_policy.iam_access.policy == "{\"Sid\": \"IAMAccess\"}"
    error_message = "Should be: {\"Sid\": \"IAMAccess\"}"
  }
  assert {
    condition     = data.aws_iam_policy_document.iam_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.iam_access.statement[0].actions == toset([
      "iam:AttachRolePolicy",
      "iam:DetachRolePolicy",
      "iam:CreatePolicy",
      "iam:DeletePolicy",
      "iam:CreateRole",
      "iam:DeleteRole",
      "iam:TagRole",
      "iam:PutRolePolicy",
      "iam:GetRole",
      "iam:ListRolePolicies",
      "iam:GetRolePolicy",
      "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole",
      "iam:DeleteRolePolicy",
      "iam:UpdateAssumeRolePolicy",
      "iam:TagRole"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.iam_access.statement[0].resources == toset([
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*-test-application-*-conduitEcsTask",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*-S3MigrationRole",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/test-application-*-exec",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/test-application-*-task",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*-copy-pipeline-*",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/test-application-test-env-codebase-pipeline-deploy",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/test-application-test-env-*-conduit-task-role",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/test-application-test-env-*-conduit-exec-role",
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.iam_access.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.iam_access.statement[1].actions == toset([
      "iam:UpdateAssumeRolePolicy"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.iam_access.statement[1].resources == toset([
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/test-application-test-env-*-lambda-role"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.iam_access.statement[2].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.iam_access.statement[2].actions == toset([
      "iam:GetPolicy",
      "iam:GetPolicyVersion"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.iam_access.statement[2].resources == toset([
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/test-application/codebuild/*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.iam_access.statement[3].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.iam_access.statement[3].actions == toset([
      "iam:ListAccountAliases"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.iam_access.statement[3].resources == toset([
      "*"
    ])
    error_message = "Unexpected resources"
  }
}

run "environment_deploy_iam_alb_cdn_cert_access" {
  command = plan

  assert {
    condition     = aws_iam_policy.alb_cdn_cert_access.name == "alb-cdn-cert-access"
    error_message = "Unexpected name"
  }
  assert {
    condition     = aws_iam_policy.alb_cdn_cert_access.policy == "{\"Sid\": \"ALBAccess\"}"
    error_message = "Unexpected policy"
  }
  assert {
    condition     = data.aws_iam_policy_document.alb_cdn_cert_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[0].actions == toset([
      "sts:AssumeRole"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[0].resources == toset([
      "arn:aws:iam::${local.dns_account_id}:role/environment-pipeline-assumed-role"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.alb_cdn_cert_access.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[1].actions == toset([
      "elasticloadbalancing:DescribeTargetGroups",
      "elasticloadbalancing:DescribeTargetGroupAttributes",
      "elasticloadbalancing:DescribeTags",
      "elasticloadbalancing:DescribeLoadBalancers",
      "elasticloadbalancing:DescribeLoadBalancerAttributes",
      "elasticloadbalancing:DescribeSSLPolicies",
      "elasticloadbalancing:DescribeListeners",
      "elasticloadbalancing:DescribeTargetHealth",
      "elasticloadbalancing:DescribeRules",
      "elasticloadbalancing:DescribeListenerCertificates",
      "elasticloadbalancing:DescribeListenerAttributes"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[1].resources == toset([
      "*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.alb_cdn_cert_access.statement[2].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[2].actions == toset([
      "elasticloadbalancing:CreateTargetGroup",
      "elasticloadbalancing:AddTags",
      "elasticloadbalancing:ModifyTargetGroupAttributes",
      "elasticloadbalancing:DeleteTargetGroup"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[2].resources == toset([
      "arn:aws:elasticloadbalancing:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:targetgroup/test-application-test-env-http/*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.alb_cdn_cert_access.statement[3].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[3].actions == toset([
      "elasticloadbalancing:CreateLoadBalancer",
      "elasticloadbalancing:AddTags",
      "elasticloadbalancing:ModifyLoadBalancerAttributes",
      "elasticloadbalancing:DeleteLoadBalancer",
      "elasticloadbalancing:CreateListener",
      "elasticloadbalancing:ModifyListener",
      "elasticloadbalancing:SetWebACL"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[3].resources == toset([
      "arn:aws:elasticloadbalancing:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:loadbalancer/app/test-application-test-env/*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.alb_cdn_cert_access.statement[4].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[4].actions == toset([
      "elasticloadbalancing:AddTags",
      "elasticloadbalancing:ModifyListener"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[4].resources == toset([
      "arn:aws:elasticloadbalancing:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:listener/app/test-application-test-env/*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.alb_cdn_cert_access.statement[5].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[5].actions == toset([
      "cloudfront:ListCachePolicies",
      "cloudfront:GetCachePolicy"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[5].resources == toset([
      "arn:aws:cloudfront::${data.aws_caller_identity.current.account_id}:cache-policy/*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.alb_cdn_cert_access.statement[6].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[6].actions == toset([
      "acm:RequestCertificate",
      "acm:AddTagsToCertificate",
      "acm:DescribeCertificate",
      "acm:ListTagsForCertificate",
      "acm:DeleteCertificate"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[6].resources == toset([
      "arn:aws:acm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:certificate/*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.alb_cdn_cert_access.statement[7].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[7].actions == toset([
      "acm:ListCertificates",
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[7].resources == toset([
      "*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.alb_cdn_cert_access.statement[8].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[8].actions == toset([
      "lambda:GetPolicy",
      "lambda:RemovePermission",
      "lambda:DeleteFunction",
      "lambda:TagResource",
      "lambda:PutFunctionConcurrency",
      "lambda:AddPermission",
      "lambda:DeleteFunction"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[8].resources == toset([
      "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:test-application-test-env-origin-secret-rotate"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.alb_cdn_cert_access.statement[9].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[9].actions == toset([
      "lambda:GetLayerVersion"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[9].resources == toset([
      "arn:aws:lambda:eu-west-2:763451185160:layer:python-requests:8"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.alb_cdn_cert_access.statement[10].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[10].actions == toset([
      "wafv2:GetWebACL",
      "wafv2:GetWebACLForResource",
      "wafv2:ListTagsForResource",
      "wafv2:DeleteWebACL",
      "wafv2:CreateWebACL",
      "wafv2:TagResource",
      "wafv2:AssociateWebACL"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[10].resources == toset([
      "arn:aws:wafv2:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:regional/webacl/*/*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.alb_cdn_cert_access.statement[11].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[11].actions == toset([
      "wafv2:CreateWebACL"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[11].resources == toset([
      "arn:aws:wafv2:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:regional/managedruleset/*/*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.alb_cdn_cert_access.statement[12].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[12].actions == toset([
      "secretsmanager:DescribeSecret",
      "secretsmanager:GetSecretValue",
      "secretsmanager:GetResourcePolicy",
      "secretsmanager:DeleteResourcePolicy",
      "secretsmanager:CancelRotateSecret",
      "secretsmanager:DeleteSecret",
      "secretsmanager:CreateSecret",
      "secretsmanager:TagResource",
      "secretsmanager:PutResourcePolicy",
      "secretsmanager:PutSecretValue",
      "secretsmanager:RotateSecret"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[12].resources == toset([
      "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:test-application-test-env-origin-verify-header-secret-*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.alb_cdn_cert_access.statement[13].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[13].actions == toset([
      "iam:TagRole"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.alb_cdn_cert_access.statement[13].resources == toset([
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/test-application-test-env-origin-secret-rotate-role"
    ])
    error_message = "Unexpected resources"
  }
}

run "environment_deploy_iam_redis_access" {
  command = plan

  assert {
    condition     = aws_iam_policy.redis_access.name == "redis-access"
    error_message = "Unexpected name"
  }
  assert {
    condition     = aws_iam_policy.redis_access.policy == "{\"Sid\": \"RedisAccess\"}"
    error_message = "Unexpected policy"
  }
  assert {
    condition     = data.aws_iam_policy_document.redis_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.redis_access.statement[0].actions == toset([
      "elasticache:CreateCacheSubnetGroup",
      "elasticache:AddTagsToResource",
      "elasticache:DescribeCacheSubnetGroups",
      "elasticache:ListTagsForResource",
      "elasticache:DeleteCacheSubnetGroup",
      "elasticache:CreateReplicationGroup"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.redis_access.statement[0].resources == toset([
      "arn:aws:elasticache:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:subnetgroup:*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.redis_access.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.redis_access.statement[1].actions == toset([
      "elasticache:AddTagsToResource",
      "elasticache:CreateReplicationGroup",
      "elasticache:DecreaseReplicaCount",
      "elasticache:DeleteReplicationGroup",
      "elasticache:DescribeReplicationGroups",
      "elasticache:IncreaseReplicaCount",
      "elasticache:ListTagsForResource",
      "elasticache:ModifyReplicationGroup",
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.redis_access.statement[1].resources == toset([
      "arn:aws:elasticache:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:replicationgroup:*",
      "arn:aws:elasticache:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parametergroup:*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.redis_access.statement[2].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.redis_access.statement[2].actions == toset([
      "elasticache:DescribeCacheClusters"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.redis_access.statement[2].resources == toset([
      "arn:aws:elasticache:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:cluster:*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.redis_access.statement[3].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.redis_access.statement[3].actions == toset([
      "elasticache:DescribeCacheEngineVersions"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.redis_access.statement[3].resources == toset([
      "*"
    ])
    error_message = "Unexpected resources"
  }
}

run "environment_deploy_iam_postgres_access" {
  command = plan

  assert {
    condition     = aws_iam_policy.postgres_access.name == "postgres-access"
    error_message = "Unexpected name"
  }
  assert {
    condition     = aws_iam_policy.postgres_access.policy == "{\"Sid\": \"PostgresAccess\"}"
    error_message = "Unexpected policy"
  }
  assert {
    condition     = data.aws_iam_policy_document.postgres_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[0].actions == toset([
      "iam:PassRole"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[0].resources == toset([
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/test-application-adminrole",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*-copy-pipeline-*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.postgres_access.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[1].actions == toset([
      "iam:CreateRole",
      "iam:GetRole",
      "iam:ListRolePolicies",
      "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole",
      "iam:DeleteRole",
      "iam:AttachRolePolicy",
      "iam:PutRolePolicy",
      "iam:GetRolePolicy",
      "iam:DeleteRolePolicy",
      "iam:PassRole",
      "iam:UpdateAssumeRolePolicy",
      "iam:DetachRolePolicy"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[1].resources == toset([
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/test-application-test-env-*",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/rds-enhanced-monitoring-*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.postgres_access.statement[2].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[2].actions == toset([
      "lambda:GetFunction",
      "lambda:InvokeFunction",
      "lambda:ListVersionsByFunction",
      "lambda:GetFunctionCodeSigningConfig",
      "lambda:UpdateFunctionCode",
      "lambda:UpdateFunctionConfiguration",
      "lambda:CreateFunction",
      "lambda:DeleteFunction"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[2].resources == toset([
      "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:test-application-test-env-*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.postgres_access.statement[3].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[3].actions == toset([
      "lambda:GetLayerVersion"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[3].resources == toset([
      "arn:aws:lambda:eu-west-2:763451185160:layer:python-postgres:1"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.postgres_access.statement[4].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[4].actions == toset([
      "rds:CreateDBParameterGroup",
      "rds:AddTagsToResource",
      "rds:ModifyDBParameterGroup",
      "rds:DescribeDBParameterGroups",
      "rds:DescribeDBParameters",
      "rds:ListTagsForResource",
      "rds:CreateDBInstance",
      "rds:ModifyDBInstance",
      "rds:DeleteDBParameterGroup"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[4].resources == toset([
      "arn:aws:rds:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:pg:test-application-test-env-*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.postgres_access.statement[5].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[5].actions == toset([
      "rds:CreateDBSubnetGroup",
      "rds:AddTagsToResource",
      "rds:DescribeDBSubnetGroups",
      "rds:ListTagsForResource",
      "rds:DeleteDBSubnetGroup",
      "rds:CreateDBInstance"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[5].resources == toset([
      "arn:aws:rds:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:subgrp:test-application-test-env-*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.postgres_access.statement[6].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[6].actions == toset([
      "rds:DescribeDBInstances"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[6].resources == toset([
      "arn:aws:rds:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:db:*"
    ])
    error_message = "Unexpected resources"
  }

  assert {
    condition     = data.aws_iam_policy_document.postgres_access.statement[7].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[7].actions == toset([
      "rds:CreateDBInstance",
      "rds:AddTagsToResource",
      "rds:ModifyDBInstance"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[7].resources == toset([
      "arn:aws:rds:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:db:test-application-test-env-*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.postgres_access.statement[8].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[8].actions == toset([
      "secretsmanager:*",
    "kms:*"])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[8].resources == toset([
      "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:rds*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.postgres_access.statement[9].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[9].actions == toset([
      "ecs:ListTaskDefinitionFamilies",
      "ecs:ListTaskDefinitions",
    "ecs:DescribeTaskDefinition", ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[9].resources == toset([
      "*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.postgres_access.statement[10].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[10].actions == toset([
      "ecs:RegisterTaskDefinition",
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[10].resources == toset([
      "arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:task-definition/*",
      "arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:task-definition/"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.postgres_access.statement[11].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[11].actions == toset([
      "ecs:DeregisterTaskDefinition"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[11].resources == toset([
      "*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.postgres_access.statement[12].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[12].actions == toset([
      "codepipeline:CreatePipeline",
      "codepipeline:DeletePipeline",
      "codepipeline:GetPipeline",
      "codepipeline:UpdatePipeline",
      "codepipeline:ListTagsForResource",
      "codepipeline:TagResource"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[12].resources == toset([
      "arn:aws:codepipeline:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*-copy-pipeline",
      "arn:aws:codepipeline:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*-copy-pipeline/*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.postgres_access.statement[13].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[13].actions == toset([
      "codebuild:CreateProject",
      "codebuild:BatchGetProjects",
      "codebuild:DeleteProject",
      "codebuild:UpdateProject"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[13].resources == toset([
      "arn:aws:codebuild:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:project/*"
    ])
    error_message = "Unexpected resources"
  }

  assert {
    condition     = data.aws_iam_policy_document.postgres_access.statement[14].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[14].actions == toset([
      "scheduler:CreateSchedule",
      "scheduler:UpdateSchedule",
      "scheduler:DeleteSchedule",
      "scheduler:TagResource",
      "scheduler:GetSchedule",
      "scheduler:ListSchedules",
      "scheduler:ListTagsForResource"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.postgres_access.statement[14].resources == toset([
      "arn:aws:scheduler:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:schedule/*"
    ])
    error_message = "Unexpected resources"
  }
}

run "environment_deploy_iam_s3_access" {
  command = plan

  assert {
    condition     = aws_iam_policy.s3_access.name == "s3-access"
    error_message = "Unexpected name"
  }
  assert {
    condition     = aws_iam_policy.s3_access.policy == "{\"Sid\": \"S3Access\"}"
    error_message = "Unexpected policy"
  }
  assert {
    condition     = data.aws_iam_policy_document.s3_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.s3_access.statement[0].actions == toset([
      "s3:*"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.s3_access.statement[0].resources == toset([
      "arn:aws:s3:::*"
    ])
    error_message = "Unexpected resources"
  }
}

run "environment_deploy_iam_opensearch_access" {
  command = plan

  assert {
    condition     = aws_iam_policy.opensearch_access.name == "opensearch-access"
    error_message = "Unexpected name"
  }
  assert {
    condition     = aws_iam_policy.opensearch_access.policy == "{\"Sid\": \"OpensearchAccess\"}"
    error_message = "Unexpected policy"
  }
  assert {
    condition     = data.aws_iam_policy_document.opensearch_access.statement[0].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.opensearch_access.statement[0].actions == toset([
      "es:CreateElasticsearchDomain",
      "es:AddTags",
      "es:DescribeDomain",
      "es:DescribeDomainConfig",
      "es:ListTags",
      "es:DeleteDomain",
      "es:UpdateDomainConfig"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.opensearch_access.statement[0].resources == toset([
      "arn:aws:es:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:domain/*"
    ])
    error_message = "Unexpected resources"
  }
  assert {
    condition     = data.aws_iam_policy_document.opensearch_access.statement[1].effect == "Allow"
    error_message = "Should be: Allow"
  }
  assert {
    condition = data.aws_iam_policy_document.opensearch_access.statement[1].actions == toset([
      "es:ListVersions"
    ])
    error_message = "Unexpected actions"
  }
  assert {
    condition = data.aws_iam_policy_document.opensearch_access.statement[1].resources == toset([
      "*"
    ])
    error_message = "Unexpected resources"
  }
}


