locals {
  role_name   = "${substr(var.destination_bucket_identifier, 0, 48)}-S3MigrationRole"
  policy_name = "${substr(var.destination_bucket_identifier, 0, 46)}-S3MigrationPolicy"

  bucket_list      = flatten([for source in var.sources : [source.source_bucket_arn, "${source.source_bucket_arn}/*"] if source.source_bucket_arn != ""])
  worker_role_list = [for source in var.sources : source.worker_role_arn if source.worker_role_arn != ""]
  kms_key_list     = [for source in var.sources : source.source_kms_key_arn if source.source_kms_key_arn != null]
}
