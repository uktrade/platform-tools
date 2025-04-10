resource "aws_iam_role" "s3_migration_role" {
  name               = local.role_name
  assume_role_policy = data.aws_iam_policy_document.allow_assume_role.json
}

data "aws_iam_policy_document" "allow_assume_role" {
  statement {
    sid    = "AllowAssumeWorkerRole"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = local.worker_role_list
    }

    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "s3_migration_policy_document" {
  statement {
    sid    = "AllowReadOnSourceBucket"
    effect = "Allow"

    actions = [
      "s3:ListBucket",
      "s3:GetObject",
      "s3:GetObjectTagging",
      "s3:GetObjectVersion",
      "s3:GetObjectVersionTagging"
    ]

    resources = local.bucket_list
  }

  statement {
    sid    = "AllowWriteOnDestinationBucket"
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
      var.destination_bucket_arn,
      "${var.destination_bucket_arn}/*"
    ]
  }

  statement {
    sid    = "AllowDestinationKMSEncryption"
    effect = "Allow"

    actions = [
      "kms:Encrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
    ]

    resources = [var.destination_kms_key_arn]
  }

  dynamic "statement" {
    for_each = length(local.kms_key_list) > 0 ? ["allow_kms_key"] : []

    content {
      sid    = "AllowSourceKMSDecryption"
      effect = "Allow"

      actions = [
        "kms:Decrypt",
        "kms:DescribeKey"
      ]

      resources = local.kms_key_list
    }
  }
}

resource "aws_iam_role_policy" "s3_migration_policy" {
  name   = local.policy_name
  role   = aws_iam_role.s3_migration_role.name
  policy = data.aws_iam_policy_document.s3_migration_policy_document.json
}
