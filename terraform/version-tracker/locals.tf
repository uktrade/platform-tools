locals {

  managed_by_tag = compact([
    var.environment != null && var.service_name != null ? "Service" : null,
    var.environment != null && var.service_name == null ? "Environment" : null,
    var.pipeline_type == "codebase-pipeline" ? "Codebase Pipelines" : null,
    var.pipeline_type == "environment-pipeline" ? "Environment Pipelines" : null,
  ])

  tags = merge(
    {
      application = var.application
      managed-by  = "DBT Platform - ${one(local.managed_by_tag)} Terraform"
    },
    var.environment != null ? {
      environment = var.environment
    } : {},
    var.service_name != null ? {
      service = var.service_name
    } : {},
    var.pipeline_type == "codebase-pipeline" ? {
      pipeline = "codebase-pipelines"
    } : {},
    var.pipeline_type == "environment-pipeline" ? {
      pipeline = "environment-pipelines"
    } : {}
  )

  parameter_name_parts = compact([
    "/platform/version/applications",
    var.application,
    var.environment != null ? "environments" : null,
    var.environment,
    var.service_name != null ? "services" : null,
    var.service_name,
    var.pipeline_type == "codebase-pipeline" ? "codebase-pipelines" : null,
    var.pipeline_type == "environment-pipeline" ? "environment-pipelines" : null,
  ])

  parameter_name = join("/", local.parameter_name_parts)
}
