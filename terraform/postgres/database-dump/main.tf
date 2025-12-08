data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

data "aws_iam_policy_document" "allow_task_creation" {
  statement {
    sid    = "AllowPullFromEcr"
    effect = "Allow"
    actions = [
      "ecr:GetAuthorizationToken",
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage"
    ]
    resources = [local.ecr_repository_arn]
  }

  statement {
    sid    = "AllowLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = [
      "arn:aws:logs:${local.region_account}:log-group:/ecs/${local.task_name}",
      "arn:aws:logs:${local.region_account}:log-group:/ecs/${local.task_name}:log-stream:*",
    ]
  }
}

data "aws_iam_policy_document" "assume_ecs_task_role" {
  policy_id = "assume_ecs_task_role"
  statement {
    sid    = "AllowECSAssumeRole"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }

  dynamic "statement" {
    for_each = local.pipeline_tasks
    content {
      sid    = "AllowPipelineAssumeRole${title(statement.value.to)}"
      effect = "Allow"

      principals {
        type        = "AWS"
        identifiers = ["arn:aws:iam::${statement.value.to_account}:role/${var.database_name}-${statement.value.from}-to-${statement.value.to}-copy-pipeline-codebuild"]
      }

      actions = ["sts:AssumeRole"]
    }
  }
}

resource "aws_iam_role" "data_dump_task_execution_role" {
  name               = "${local.task_name}-exec"
  assume_role_policy = data.aws_iam_policy_document.assume_ecs_task_role.json

  tags = local.tags
}

resource "aws_iam_role_policy" "allow_task_creation" {
  name   = "AllowTaskCreation"
  role   = aws_iam_role.data_dump_task_execution_role.name
  policy = data.aws_iam_policy_document.allow_task_creation.json
}

data "aws_iam_policy_document" "data_dump" {
  policy_id = "data_dump"
  statement {
    sid    = "AllowWriteToS3"
    effect = "Allow"

    actions = [
      "s3:ListBucket",
      "s3:PutObject",
      "s3:PutObjectAcl",
      "s3:PutObjectTagging",
      "s3:GetObjectTagging",
      "s3:GetObjectVersion",
      "s3:GetObjectVersionTagging"
    ]

    resources = [
      aws_s3_bucket.data_dump_bucket.arn,
      "${aws_s3_bucket.data_dump_bucket.arn}/*"
    ]
  }

  statement {
    sid    = "AllowKMSEncryption"
    effect = "Allow"

    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
    ]

    resources = [aws_kms_key.data_dump_kms_key.arn]
  }
}

resource "aws_iam_role" "data_dump" {
  name               = "${local.task_name}-task"
  assume_role_policy = data.aws_iam_policy_document.assume_ecs_task_role.json

  tags = local.tags
}

resource "aws_iam_role_policy" "allow_data_dump" {
  name   = "AllowDataDump"
  role   = aws_iam_role.data_dump.name
  policy = data.aws_iam_policy_document.data_dump.json
}

resource "aws_iam_role_policy" "allow_pipeline_access" {
  for_each = toset(length(local.pipeline_tasks) > 0 ? [""] : [])
  name     = "AllowPipelineAccess"
  role     = aws_iam_role.data_dump.name
  policy   = data.aws_iam_policy_document.pipeline_access.json
}

data "aws_iam_policy_document" "pipeline_access" {
  policy_id = "pipeline_access"
  statement {
    sid    = "AllowListAccountAliases"
    effect = "Allow"
    actions = [
      "iam:ListAccountAliases",
    ]
    resources = [
      "*",
    ]
  }

  statement {
    sid    = "AllowGetCopilotMetaData"
    effect = "Allow"
    actions = [
      "ssm:GetParametersByPath",
      "ssm:GetParameters",
      "ssm:GetParameter"
    ]
    resources = [
      "arn:aws:ssm:${local.region_account}:parameter/copilot/*",
      "arn:aws:ssm:${local.region_account}:parameter/platform/applications/*"
    ]
  }

  statement {
    sid    = "AllowReadOnRDSSecrets"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
    ]
    resources = [
      "arn:aws:secretsmanager:${local.region_account}:secret:rds*"
    ]
  }

  statement {
    sid    = "AllowRunningDumpTask"
    effect = "Allow"
    actions = [
      "ecs:RunTask",
    ]
    resources = [
      "arn:aws:ecs:${local.region_account}:task-definition/*-dump:*"
    ]
  }

  statement {
    sid    = "AllowLogTrail"
    effect = "Allow"
    actions = [
      "logs:StartLiveTail",
    ]
    resources = [
      "arn:aws:logs:${local.region_account}:log-group:/ecs/*-dump"
    ]
  }

  statement {
    sid    = "AllowPassRoleToTaskExec"
    effect = "Allow"
    actions = [
      "iam:PassRole",
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*-dump-exec"
    ]
  }

  statement {
    sid    = "AllowDescribeLogs"
    effect = "Allow"
    actions = [
      "logs:DescribeLogGroups",
    ]
    resources = [
      "arn:aws:logs:${local.region_account}:log-group::log-stream:"
    ]
  }

  statement {
    sid = "AllowRedisListVersions"
    actions = [
      "elasticache:DescribeCacheEngineVersions"
    ]
    effect = "Allow"
    resources = [
      "*"
    ]
  }

  statement {
    sid = "AllowOpensearchListVersions"
    actions = [
      "es:ListVersions",
      "es:ListElasticsearchVersions"
    ]
    effect = "Allow"
    resources = [
      "*"
    ]
  }

  statement {
    sid    = "AllowDescribeVPCsAndSubnets"
    effect = "Allow"
    actions = [
      "ec2:DescribeVpcs",
      "ec2:DescribeSubnets",
      "ec2:DescribeRouteTables",
      "ec2:DescribeSecurityGroups"
    ]
    resources = [
      "*"
    ]
  }
}

resource "aws_ecs_task_definition" "service" {
  # checkov:skip=CKV_AWS_336: Needs write access to filesystem for database dump
  family = local.task_name
  container_definitions = jsonencode([
    {
      name      = local.task_name
      image     = "public.ecr.aws/uktrade/database-copy:tag-latest"
      essential = true
      environment = [
        {
          name  = "DB_CONNECTION_STRING"
          value = "provided during task creation"
        },
        {
          name  = "DATA_COPY_OPERATION"
          value = "DUMP"
        },
        {
          name  = "S3_BUCKET_NAME"
          value = aws_s3_bucket.data_dump_bucket.bucket
        }
      ],
      portMappings = [
        {
          containerPort = 80
          hostPort      = 80
        }
      ]
      logConfiguration = {
        logDriver = "awslogs",
        options = {
          awslogs-group         = "/ecs/${local.task_name}"
          awslogs-region        = "eu-west-2"
          mode                  = "non-blocking"
          awslogs-create-group  = "true"
          max-buffer-size       = "25m"
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  cpu    = 1024
  memory = 3072

  requires_compatibilities = ["FARGATE"]

  task_role_arn      = aws_iam_role.data_dump.arn
  execution_role_arn = aws_iam_role.data_dump_task_execution_role.arn
  network_mode       = "awsvpc"

  runtime_platform {
    cpu_architecture        = "ARM64"
    operating_system_family = "LINUX"
  }
}

resource "aws_s3_bucket" "data_dump_bucket" {
  # checkov:skip=CKV_AWS_144: Cross Region Replication not Required
  # checkov:skip=CKV2_AWS_62: Requires wider discussion around log/event ingestion before implementing. To be picked up on conclusion of DBTP-974
  # checkov:skip=CKV2_AWS_61: This bucket is used for ephemeral data transfer - we do not need lifecycle configuration
  # checkov:skip=CKV_AWS_21: This bucket is used for ephemeral data transfer - we do not want versioning
  # checkov:skip=CKV_AWS_18:  Requires wider discussion around log/event ingestion before implementing. To be picked up on conclusion of DBTP-974
  bucket = local.dump_bucket_name
  tags   = local.tags
}

data "aws_iam_policy_document" "data_dump_bucket_policy" {
  policy_id = "data_dump_bucket_policy"

  statement {
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    actions = [
      "s3:*",
    ]
    effect = "Deny"
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values = [
        "false",
      ]
    }
    resources = [
      aws_s3_bucket.data_dump_bucket.arn,
      "${aws_s3_bucket.data_dump_bucket.arn}/*",
    ]
  }

  statement {
    effect = "Allow"
    principals {
      type = "AWS"
      identifiers = [
        for el in var.tasks :
        "arn:aws:iam::${el.to_account}:role/${var.application}-${el.to}-${var.database_name}-load-task"
      ]
    }
    actions = [
      "s3:ListBucket",
      "s3:GetObject",
      "s3:GetObjectTagging",
      "s3:GetObjectVersion",
      "s3:GetObjectVersionTagging",
      "s3:DeleteObject"
    ]
    resources = [
      aws_s3_bucket.data_dump_bucket.arn,
      "${aws_s3_bucket.data_dump_bucket.arn}/*",
    ]
  }
}

resource "aws_s3_bucket_policy" "data_dump_bucket_policy" {
  bucket = aws_s3_bucket.data_dump_bucket.id
  policy = data.aws_iam_policy_document.data_dump_bucket_policy.json
}

resource "aws_kms_key" "data_dump_kms_key" {
  # checkov:skip=CKV_AWS_7:We are not currently rotating the keys
  description = "KMS Key for S3 encryption"
  tags        = local.tags

  policy = jsonencode({
    Statement = [
      {
        "Sid" : "Enable IAM User Permissions",
        "Effect" : "Allow",
        "Principal" : {
          "AWS" : flatten([
            "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root",
            [for el in var.tasks :
              "arn:aws:iam::${el.to_account}:role/${var.application}-${el.to}-${var.database_name}-load-task"
            ]
          ])
        },
        "Action" : "kms:*",
        "Resource" : "*"
      }
    ]
    Version = "2012-10-17"
  })
}

resource "aws_kms_alias" "data_dump_kms_alias" {
  depends_on    = [aws_kms_key.data_dump_kms_key]
  name          = local.dump_kms_key_alias
  target_key_id = aws_kms_key.data_dump_kms_key.id
}

resource "aws_s3_bucket_server_side_encryption_configuration" "encryption-config" {
  # checkov:skip=CKV2_AWS_67:We are not currently rotating the keys
  bucket = aws_s3_bucket.data_dump_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.data_dump_kms_key.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "public_access_block" {
  bucket                  = aws_s3_bucket.data_dump_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
