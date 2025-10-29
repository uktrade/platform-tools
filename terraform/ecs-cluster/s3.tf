resource "aws_s3_bucket" "task_definitions" {
  # checkov:skip=CKV_AWS_144: Cross Region Replication not Required
  # checkov:skip=CKV2_AWS_62: Don't need even notifications
  # checkov:skip=CKV_AWS_18:  Logging not required
  bucket = "ecs-task-definitions-${var.application}-${var.environment}"
  tags   = local.tags
}

resource "aws_s3_bucket_policy" "task_definitions" {
  bucket = aws_s3_bucket.task_definitions.id
  policy = data.aws_iam_policy_document.task_definitions_bucket.json
}

data "aws_iam_policy_document" "task_definitions_bucket" {
  statement {
    effect  = "Deny"
    actions = ["s3:*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }

    resources = [
      aws_s3_bucket.task_definitions.arn,
      "${aws_s3_bucket.task_definitions.arn}/*"
    ]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }

  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:DeleteObjectVersion"
    ]

    principals {
      type = "AWS"
      identifiers = [
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.application}-${var.environment}-codebase-pipeline-deploy"
      ]
    }

    resources = [
      aws_s3_bucket.task_definitions.arn,
      "${aws_s3_bucket.task_definitions.arn}/*"
    ]
  }
}

resource "aws_s3_bucket_public_access_block" "task_definitions" {
  bucket                  = aws_s3_bucket.task_definitions.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "task_definitions" {
  bucket = aws_s3_bucket.task_definitions.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_lifecycle_configuration" "task_definitions" {
  bucket = aws_s3_bucket.task_definitions.id

  rule {
    id     = "NonCurrentVersionsRetention"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }

  # To make checkov happy
  rule {
    id     = "AbortIncompleteMultipartUpload"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  depends_on = [aws_s3_bucket_versioning.task_definitions]
}

resource "aws_kms_key" "kms_key" {
  # checkov:skip=CKV_AWS_7:We are not currently rotating the keys
  description = "KMS Key for S3 encryption"
  tags        = local.tags
}

resource "aws_kms_alias" "s3-bucket" {
  name          = "alias/${var.application}-${var.environment}-task-def-key"
  target_key_id = aws_kms_key.kms_key.id
  depends_on    = [aws_kms_key.kms_key]
}

resource "aws_kms_key_policy" "key-policy" {
  key_id = aws_kms_key.kms_key.id
  policy = data.aws_iam_policy_document.key_policy.json
}

resource "aws_s3_bucket_server_side_encryption_configuration" "encryption-config" {
  bucket = aws_s3_bucket.task_definitions.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.kms_key.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

data "aws_iam_policy_document" "key_policy" {
  statement {
    sid     = "Enable IAM User Permissions"
    effect  = "Allow"
    actions = ["kms:*"]

    principals {
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
      type        = "AWS"
    }

    resources = [aws_kms_key.kms_key.arn]
  }

  statement {
    effect = "Allow"
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:DescribeKey",
    ]
    principals {
      identifiers = ["*"]
      type        = "AWS"
    }
    condition {
      test     = "StringLike"
      values   = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.application}-${var.environment}-codebase-pipeline-deploy"]
      variable = "aws:PrincipalArn"
    }
    resources = [aws_kms_key.kms_key.arn]
  }
}
