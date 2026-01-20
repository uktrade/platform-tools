resource "aws_s3_bucket" "artifact_store" {
  # checkov:skip=CKV_AWS_144: It's just a pipeline artifacts bucket, cross-region replication is not needed.
  # checkov:skip=CKV2_AWS_62: It's just a pipeline artifacts bucket, event notifications are not needed.
  # checkov:skip=CKV_AWS_21: It's just a pipeline artifacts bucket, versioning is not needed.
  # checkov:skip=CKV_AWS_18: It's just a pipeline artifacts bucket, access logging is not needed.
  bucket = "${var.application}-${var.codebase}-cb-arts"

  tags = local.tags
}

resource "aws_s3_bucket_lifecycle_configuration" "lifecycle_rule" {
  bucket = aws_s3_bucket.artifact_store.id

  rule {
    id     = "delete-after-60-days"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }

    expiration {
      days = 60
    }
  }
}

data "aws_iam_policy_document" "artifact_store_bucket_policy" {
  statement {
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    actions = [
      "s3:*"
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
      aws_s3_bucket.artifact_store.arn,
      "${aws_s3_bucket.artifact_store.arn}/*",
    ]
  }

  statement {
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = [for id in local.deploy_account_ids : "arn:aws:iam::${id}:root"]
    }
    condition {
      test = "ArnLike"
      values = [
        for id in local.deploy_account_ids :
        "arn:aws:iam::${id}:role/${var.application}-*-codebase-pipeline-deploy"
      ]
      variable = "aws:PrincipalArn"
    }
    actions = [
      "s3:*"
    ]
    resources = [
      aws_s3_bucket.artifact_store.arn,
      "${aws_s3_bucket.artifact_store.arn}/*",
    ]
  }
}

resource "aws_s3_bucket_policy" "artifact_store_bucket_policy" {
  bucket = aws_s3_bucket.artifact_store.id
  policy = data.aws_iam_policy_document.artifact_store_bucket_policy.json
}

resource "aws_kms_key" "artifact_store_kms_key" {
  # checkov:skip=CKV_AWS_7:We are not currently rotating the keys
  description = "KMS Key for S3 encryption"
  tags        = local.tags

  policy = jsonencode({
    Statement = [
      {
        "Sid" : "Enable IAM User Permissions",
        "Effect" : "Allow",
        "Principal" : {
          "AWS" : [for id in local.deploy_account_ids : "arn:aws:iam::${id}:root"]
        },
        "Action" : "kms:*",
        "Resource" : "*"
      }
    ]
    Version = "2012-10-17"
  })
}

resource "aws_kms_alias" "artifact_store_kms_alias" {
  depends_on    = [aws_kms_key.artifact_store_kms_key]
  name          = "alias/${var.application}-${var.codebase}-cb-arts-key"
  target_key_id = aws_kms_key.artifact_store_kms_key.id
}

resource "aws_s3_bucket_server_side_encryption_configuration" "encryption-config" {
  # checkov:skip=CKV2_AWS_67:We are not currently rotating the keys
  bucket = aws_s3_bucket.artifact_store.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.artifact_store_kms_key.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "public_access_block" {
  bucket                  = aws_s3_bucket.artifact_store.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
