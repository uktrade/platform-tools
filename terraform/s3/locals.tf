locals {
  tags = {
    application         = var.application
    environment         = var.environment
    managed-by          = "Meeee!"
    copilot-application = var.application
    copilot-environment = var.environment
  }

  kms_alias_name = "${var.application}-${var.environment}-${var.config.bucket_name}-key"

  has_data_migration_import_enabled = try(coalesce(var.config.data_migration.import_sources, [var.config.data_migration.import]) != null, false)
}
