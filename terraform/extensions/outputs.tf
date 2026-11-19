output "resolved_config" {
  value = local.extensions
}

output "sqs" {
  value = local.sqs
}

output "extensions_with_default_and_environment_settings_merged" {
  value = local.extensions_with_default_and_environment_settings_merged
}

output "extensions_for_environment" {
  value = local.extensions_for_environment
}

output "var_args_services" {
  value = var.args.services
}