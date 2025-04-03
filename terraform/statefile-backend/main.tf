data "aws_caller_identity" "current" {}
resource "aws_s3_bucket" "terraform-state" {
  # checkov:skip=CKV_AWS_144: Cross Region Replication not Required
  # checkov:skip=CKV2_AWS_62: Requires wider discussion around log/event ingestion before implementing. To be picked up on conclusion of DBTP-974
  # checkov:skip=CKV2_AWS_61: This bucket is only used for the TF state, so no requirement for lifecycle configuration
  # checkov:skip=CKV_AWS_18:  Requires wider discussion around log/event ingestion before implementing. To be picked up on conclusion of DBTP-974
  bucket = "terraform-platform-state-${var.aws_account_name}"

  tags = merge(
    local.tags,
    {
      purpose = "Terraform statefile storage - DBT Platform"
    }
  )
}

resource "aws_s3_bucket_acl" "terraform-state-acl" {
  depends_on = [aws_s3_bucket_ownership_controls.terraform-state-ownership]
  bucket     = aws_s3_bucket.terraform-state.id
  acl        = "private"
}

resource "aws_s3_bucket_versioning" "terraform-state-versioning" {
  bucket = aws_s3_bucket.terraform-state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_ownership_controls" "terraform-state-ownership" {
  # checkov:skip=CKV2_AWS_65: Finding is negated by aws_s3_bucket_acl.terraform-state-acl
  bucket = aws_s3_bucket.terraform-state.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_public_access_block" "block" {
  bucket = aws_s3_bucket.terraform-state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_kms_key" "terraform-bucket-key" {
  # checkov:skip=CKV_AWS_7:We are not currently rotating the keys
  description = "This key is used to encrypt bucket objects"

  policy = jsonencode({
    Id = "key-default-1"
    Statement = [
      {
        "Sid" : "Enable IAM User Permissions",
        "Effect" : "Allow",
        "Principal" : {
          "AWS" : "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        },
        "Action" : "kms:*",
        "Resource" : "*"
      }
    ]
    Version = "2012-10-17"
  })

  tags = merge(
    local.tags,
    {
      purpose = "Terraform statefile kms key - DBT Platform"
    }
  )
}

resource "aws_kms_alias" "key-alias" {
  name          = "alias/terraform-platform-state-s3-key-${var.aws_account_name}"
  target_key_id = aws_kms_key.terraform-bucket-key.key_id
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform-state-sse" {
  # checkov:skip=CKV2_AWS_67:We are not currently rotating the keys
  bucket = aws_s3_bucket.terraform-state.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.terraform-bucket-key.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_dynamodb_table" "terraform-state" {
  # checkov:skip=CKV_AWS_28:  No requirement for point in time backups of the Terraform state lock database
  # checkov:skip=CKV_AWS_119: No requirement for CMK for the Terraform state lock database
  # checkov:skip=CKV2_AWS_16: No requirement for scaling for the Terraform state lock database
  name           = "terraform-platform-lockdb-${var.aws_account_name}"
  read_capacity  = 20
  write_capacity = 20
  hash_key       = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
  tags = merge(
    local.tags,
    {
      purpose = "Terraform statefile lock - DBT Platform"
    }
  )
}
