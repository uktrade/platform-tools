data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  serve_static_domain = var.environment == "prod" ? "${var.config.bucket_name}.${var.application}.prod.uktrade.digital" : "${var.config.bucket_name}.${var.environment}.${var.application}.uktrade.digital"
  ssm_param_name      = coalesce(var.config.serve_static_param_name, "STATIC_S3_ENDPOINT")
}

resource "aws_s3_bucket" "this" {
  # checkov:skip=CKV_AWS_144: Cross Region Replication not Required
  # checkov:skip=CKV2_AWS_62: Requires wider discussion around log/event ingestion before implementing. To be picked up on conclusion of DBTP-974
  # checkov:skip=CKV_AWS_18:  Requires wider discussion around log/event ingestion before implementing. To be picked up on conclusion of DBTP-974
  bucket = var.config.serve_static_content ? local.serve_static_domain : var.config.bucket_name

  tags = local.tags
}

data "aws_iam_policy_document" "bucket-policy" {
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
      aws_s3_bucket.this.arn,
      "${aws_s3_bucket.this.arn}/*",
    ]
  }

  dynamic "statement" {
    for_each = coalesce(var.config.external_role_access, {})
    content {
      effect = "Allow"
      actions = flatten([
        statement.value.read ? ["s3:Get*", "s3:ListBucket"] : [],
        statement.value.write ? ["s3:Put*"] : [],
      ])
      principals {
        identifiers = [statement.value.role_arn]
        type        = "AWS"
      }
      resources = [aws_s3_bucket.this.arn, "${aws_s3_bucket.this.arn}/*"]
    }
  }

  dynamic "statement" {
    for_each = coalesce(var.config.cross_environment_service_access, {})
    content {
      effect = "Allow"
      actions = flatten([
        statement.value.read ? ["s3:Get*", "s3:ListBucket"] : [],
        statement.value.write ? ["s3:Put*"] : [],
      ])
      principals {
        identifiers = ["*"]
        type        = "AWS"
      }
      condition {
        test     = "StringLike"
        values   = ["arn:aws:iam::${statement.value.account}:role/${var.application}-${statement.value.environment}-${statement.value.service}-TaskRole-*"]
        variable = "aws:PrincipalArn"
      }
      resources = [aws_s3_bucket.this.arn, "${aws_s3_bucket.this.arn}/*"]
    }
  }
}

resource "aws_s3_bucket_policy" "bucket-policy" {
  count = var.config.serve_static_content ? 0 : 1

  bucket = aws_s3_bucket.this.id
  policy = data.aws_iam_policy_document.bucket-policy.json
}

resource "aws_s3_bucket_versioning" "this-versioning" {
  bucket = aws_s3_bucket.this.id

  versioning_configuration {
    status = coalesce(var.config.versioning, false) ? "Enabled" : "Disabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "lifecycle-configuration" {
  count = var.config.lifecycle_rules != null ? 1 : 0

  bucket = aws_s3_bucket.this.id

  # checkov:skip=CKV_AWS_300: Ensure S3 lifecycle configuration sets period for aborting failed uploads
  dynamic "rule" {
    for_each = var.config.lifecycle_rules
    content {
      id = "rule-${index(var.config.lifecycle_rules, rule.value) + 1}"
      abort_incomplete_multipart_upload {
        days_after_initiation = 7
      }
      filter {
        prefix = rule.value.filter_prefix
      }
      expiration {
        days = rule.value.expiration_days
      }
      status = coalesce(rule.value.enabled, false) ? "Enabled" : "Disabled"
    }
  }
}

data "aws_iam_policy_document" "key-policy" {
  count = var.config.serve_static_content ? 0 : 1
  statement {
    sid       = "Enable IAM User Permissions"
    effect    = "Allow"
    actions   = ["kms:*"]
    resources = [aws_kms_key.kms-key[0].arn]
    principals {
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
      type        = "AWS"
    }
  }

  dynamic "statement" {
    for_each = coalesce(var.config.external_role_access, {})
    content {
      effect = "Allow"
      actions = flatten([
        statement.value.read ? ["kms:Decrypt"] : [],
        statement.value.write ? ["kms:GenerateDataKey"] : [],
      ])
      principals {
        identifiers = [statement.value.role_arn]
        type        = "AWS"
      }
      resources = [aws_kms_key.kms-key[0].arn]
    }
  }

  dynamic "statement" {
    for_each = coalesce(var.config.cross_environment_service_access, {})
    content {
      effect = "Allow"
      actions = flatten([
        statement.value.read ? ["kms:Decrypt"] : [],
        statement.value.write ? ["kms:GenerateDataKey"] : [],
      ])
      principals {
        identifiers = ["*"]
        type        = "AWS"
      }
      condition {
        test     = "StringLike"
        values   = ["arn:aws:iam::${statement.value.account}:role/${var.application}-${statement.value.environment}-${statement.value.service}-TaskRole-*"]
        variable = "aws:PrincipalArn"
      }
      resources = [aws_kms_key.kms-key[0].arn]
    }
  }
}

resource "aws_kms_key_policy" "key-policy" {
  count  = var.config.serve_static_content ? 0 : 1
  key_id = aws_kms_key.kms-key[0].id
  policy = data.aws_iam_policy_document.key-policy[0].json
}

resource "aws_kms_key" "kms-key" {
  count = var.config.serve_static_content ? 0 : 1

  # checkov:skip=CKV_AWS_7:We are not currently rotating the keys
  description = "KMS Key for S3 encryption"
  tags        = local.tags
}

resource "aws_kms_alias" "s3-bucket" {
  count = var.config.serve_static_content ? 0 : 1

  depends_on    = [aws_kms_key.kms-key]
  name          = "alias/${local.kms_alias_name}"
  target_key_id = aws_kms_key.kms-key[0].id
}

resource "aws_s3_bucket_server_side_encryption_configuration" "encryption-config" {
  count = var.config.serve_static_content ? 0 : 1

  # checkov:skip=CKV2_AWS_67:We are not currently rotating the keys
  bucket = aws_s3_bucket.this.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.kms-key[0].arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_object_lock_configuration" "object-lock-config" {
  count = var.config.retention_policy != null ? 1 : 0

  bucket = aws_s3_bucket.this.id

  rule {
    default_retention {
      mode  = var.config.retention_policy.mode
      days  = lookup(var.config.retention_policy, "days", null)
      years = lookup(var.config.retention_policy, "years", null)
    }
  }
}

// create objects based on the config.objects key
resource "aws_s3_object" "object" {
  for_each = {
    for item in coalesce(var.config.objects, []) : item.key => {
      body         = item.body
      content_type = item.content_type
    }
  }

  bucket  = aws_s3_bucket.this.id
  key     = each.key
  content = each.value.body

  content_type = each.value.content_type

  kms_key_id             = var.config.serve_static_content ? null : aws_kms_key.kms-key[0].arn
  server_side_encryption = var.config.serve_static_content ? null : "aws:kms"
}


resource "aws_s3_bucket_public_access_block" "public_access_block" {
  bucket                  = aws_s3_bucket.this.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

// Cloudfront resources for serving static content

resource "aws_cloudfront_origin_access_control" "oac" {
  count = !var.config.managed_ingress && var.config.serve_static_content ? 1 : 0

  name                              = "${var.config.bucket_name}.${var.environment}.${var.application}-oac"
  provider                          = aws.domain-cdn
  description                       = "Origin access control for Cloudfront distribution and ${local.serve_static_domain} static s3 bucket."
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
  lifecycle {
    prevent_destroy = true
  }
}

# # Attach a bucket policy to allow CloudFront to access the bucket
resource "aws_s3_bucket_policy" "cloudfront_bucket_policy" {
  count = !var.config.managed_ingress && var.config.serve_static_content ? 1 : 0

  bucket = aws_s3_bucket.this.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = ["${aws_s3_bucket.this.arn}/*", aws_s3_bucket.this.arn]
        Condition = {
          # We trust any CDN in the relevant AWS account (dev or live).
          # TODO(DBTP-2714): Restrict access so that only the CDN belonging to
          # this application + environment + bucket name is trusted.
          StringLike = {
            "AWS:SourceArn" = "arn:aws:cloudfront::${var.cdn_account_id}:distribution/*"
          }
        }
      }
    ]
  })
}

resource "aws_acm_certificate" "certificate" {
  count = !var.config.managed_ingress && var.config.serve_static_content ? 1 : 0

  provider          = aws.domain-cdn
  domain_name       = local.serve_static_domain
  validation_method = "DNS"

  lifecycle {
    prevent_destroy = true
    create_before_destroy = true
  }

  tags = local.tags
}

data "aws_route53_zone" "selected" {
  count = !var.config.managed_ingress && var.config.serve_static_content ? 1 : 0

  provider     = aws.domain-cdn
  name         = var.environment == "prod" ? "${var.application}.prod.uktrade.digital" : "${var.application}.uktrade.digital"
  private_zone = false
}

resource "aws_route53_record" "cert_validation" {
  count = !var.config.managed_ingress && var.config.serve_static_content ? 1 : 0

  provider = aws.domain-cdn

  name            = element(aws_acm_certificate.certificate[0].domain_validation_options[*].resource_record_name, 0)
  type            = element(aws_acm_certificate.certificate[0].domain_validation_options[*].resource_record_type, 0)
  zone_id         = data.aws_route53_zone.selected[0].id
  records         = [element(aws_acm_certificate.certificate[0].domain_validation_options[*].resource_record_value, 0)]
  ttl             = 60
  depends_on      = [aws_acm_certificate.certificate]
  allow_overwrite = true
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_acm_certificate_validation" "certificate_validation" {
  count = !var.config.managed_ingress && var.config.serve_static_content ? 1 : 0

  provider                = aws.domain-cdn
  certificate_arn         = aws_acm_certificate.certificate[0].arn
  validation_record_fqdns = [aws_route53_record.cert_validation[0].fqdn]
  depends_on              = [aws_route53_record.cert_validation]
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_route53_record" "cloudfront_domain" {
  count = !var.config.managed_ingress && var.config.serve_static_content ? 1 : 0

  provider = aws.domain-cdn
  name     = aws_s3_bucket.this.bucket
  type     = "A"
  zone_id  = data.aws_route53_zone.selected[0].id
  alias {
    name                   = aws_cloudfront_distribution.s3_distribution[0].domain_name
    zone_id                = aws_cloudfront_distribution.s3_distribution[0].hosted_zone_id
    evaluate_target_health = false
  }
  lifecycle {
    prevent_destroy = true
  }
}

data "aws_cloudfront_cache_policy" "example" {
  name = "Managed-CachingOptimized"
}

resource "aws_cloudfront_distribution" "s3_distribution" {
  # checkov:skip=CKV2_AWS_32: Ensure CloudFront distribution has a response headers policy attached
  # not required now
  # checkov:skip=CKV2_AWS_47: Ensure AWS CloudFront attached WAFv2 WebACL is configured with AMR for Log4j Vulnerability
  # checkov:skip=CKV_AWS_68: CloudFront Distribution should have WAF enabled
  # No WAF rules for S3 endpoints set up by Cyber yet
  # checkov:skip=CKV_AWS_86: Ensure CloudFront distribution has Access Logging enabled
  # we don't enable access logging for s3 buckets and it means maintaining another bucket for logs
  # checkov:skip=CKV_AWS_305: Ensure CloudFront distribution has a default root object configured
  # we want individual service teams to decide what objects each bucket contains
  # checkov:skip=CKV_AWS_310: Ensure CloudFront distributions should have origin failover configured
  # we don't enable origin failover for s3 buckets and it means maintaining another bucket
  # checkov:skip=CKV_AWS_374: Global access required for static content via S3

  count = !var.config.managed_ingress && var.config.serve_static_content ? 1 : 0

  provider = aws.domain-cdn
  aliases  = [local.serve_static_domain]

  origin {
    domain_name = aws_s3_bucket.this.bucket_regional_domain_name
    origin_id   = "S3-${aws_s3_bucket.this.bucket}"

    origin_access_control_id = aws_cloudfront_origin_access_control.oac[0].id
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.this.bucket}"

    viewer_protocol_policy = "redirect-to-https"
    cache_policy_id        = data.aws_cloudfront_cache_policy.example.id
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.certificate[0].arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  enabled = true

  tags = local.tags
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_kms_key" "s3-ssm-kms-key" {
  count               = var.config.serve_static_content ? 1 : 0
  description         = "KMS Key for ${var.application}-${var.environment} S3 module SSM parameter encryption"
  enable_key_rotation = true
  tags                = local.tags
}

resource "aws_kms_key_policy" "s3-ssm-kms-key-policy" {
  count  = var.config.serve_static_content ? 1 : 0
  key_id = aws_kms_key.s3-ssm-kms-key[0].id
  policy = data.aws_iam_policy_document.s3-ssm-kms-key-policy-document[0].json
}

data "aws_iam_policy_document" "s3-ssm-kms-key-policy-document" {
  count   = var.config.serve_static_content ? 1 : 0
  version = "2012-10-17"

  statement {
    sid       = "Enable SSM Permissions"
    effect    = "Allow"
    actions   = ["kms:GenerateDataKey*", "kms:Decrypt"]
    resources = [aws_kms_key.s3-ssm-kms-key[0].arn]
    principals {
      type        = "Service"
      identifiers = ["ssm.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "kms:EncryptionContext:aws:ssm:parameterName"
      values = [
        "/copilot/${var.application}/${var.environment}/secrets/${local.ssm_param_name}",
      ]
    }
  }

  statement {
    sid     = "AllowKeyAdminByRoot"
    effect  = "Allow"
    actions = ["kms:*"]
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    resources = [aws_kms_key.s3-ssm-kms-key[0].arn]
  }

  statement {
    sid     = "AllowKeyAdminBySSOAdministrator"
    effect  = "Allow"
    actions = ["kms:*"]
    principals {
      type        = "AWS"
      identifiers = ["*"]
    }
    condition {
      test     = "StringLike"
      variable = "aws:PrincipalArn"
      values = [
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/aws-reserved/sso.amazonaws.com/${data.aws_region.current.region}/AWSReservedSSO_AdministratorAccess_*"
      ]
    }
    resources = [aws_kms_key.s3-ssm-kms-key[0].arn]
  }
}

resource "aws_ssm_parameter" "cloudfront_alias" {
  count = var.config.serve_static_content ? 1 : 0

  name   = "/copilot/${var.application}/${var.environment}/secrets/${local.ssm_param_name}"
  type   = "SecureString"
  value  = local.serve_static_domain
  key_id = aws_kms_key.s3-ssm-kms-key[0].arn

  tags = local.tags
}

# Only supported for non-static S3 buckets
module "data_migration" {
  count = local.has_data_migration_import_enabled ? 1 : 0

  source = "../data-migration"

  depends_on = [
    aws_s3_bucket.this,
    aws_kms_key.kms-key
  ]

  sources = coalesce(var.config.data_migration.import_sources, [var.config.data_migration.import])

  destination_bucket_identifier = aws_s3_bucket.this.id
  destination_kms_key_arn       = aws_kms_key.kms-key[0].arn
  destination_bucket_arn        = aws_s3_bucket.this.arn
}
