mock_provider "datadog" {
  alias = "ddog"
}

variables {
  application = "test-app"
  environment = "test-env"
  repos  = ["test-repo1", "test-repo2"]
  config = {
    team_name           = "test-team",
    contact_name        = "test-contact-name",
    contact_email       = "test-contact-email",
    documentation_url   = "test-docs",
    services_to_monitor = ["test-web", "test-postgres"] #, "test-redis", "test-elasticsearch"]
  }
}

run "datadog_system_entity_test_application" {
  command = plan
  assert {
    condition     = yamldecode(datadog_software_catalog.datadog-software-catalog-system.entity).metadata.name == "${var.application}-${var.environment}"
    error_message = "Should be: metadata.name = ${var.application}-${var.environment}"
  }
}

run "datadog_system_entity_test_owner" {
  command = plan
  assert {
    condition     = yamldecode(datadog_software_catalog.datadog-software-catalog-system.entity).metadata.owner == var.config.team_name
    error_message = "Should be: metadata.owner = ${var.config.team_name}"
  }
}

run "datadog_service_entity_test_name" {
  command = plan
  assert {
    condition     = yamldecode(datadog_software_catalog.datadog-software-catalog-service["test-web"].entity).metadata.name == "${var.application}-${var.environment}-${var.config.services_to_monitor[0]}"
    error_message = "Should be: metadata.displayName = ${var.application}:${var.config.services_to_monitor[0]}"
  }
}

run "datadog_service_entity_test_parent" {
  command = plan
  assert {
    condition     = yamldecode(datadog_software_catalog.datadog-software-catalog-service["test-postgres"].entity).spec.componentOf[0] == "system:test-app-test-env"
    error_message = "Should be: spec.componentOf = system:test-app-test-env"
  }
}
