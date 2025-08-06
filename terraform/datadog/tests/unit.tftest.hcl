mock_provider "datadog" {
  alias = "ddog"
}

variables {
  application = "test-app"
  environment = "test-env"
  repos       = ["test-repo1", "test-repo2"]
  config = {
    team_name           = "test-team",
    contact_name        = "test-contact-name",
    contact_email       = "test-contact-email",
    contacts            = yamlencode({ "email" : [{ "name" : "d", "address" : "a" }] })
    documentation_url   = "test-docs",
    description         = "test application",
    services_to_monitor = { "test-web" : ["postgres", "redis"], "test-api" = ["nginx", "ipfilter"] }
  }
}

run "datadog_system_entity_test_application" {
  command = plan
  assert {
    condition     = yamldecode(datadog_software_catalog.datadog-software-catalog-system["test-web"].entity).metadata.name == "${var.application}-test-web"
    error_message = "Should be: metadata.name = ${var.application}"
  }
}

run "datadog_system_entity_test_owner" {
  command = plan
  assert {
    condition     = yamldecode(datadog_software_catalog.datadog-software-catalog-system["test-api"].entity).metadata.owner == var.config.team_name
    error_message = "Should be: metadata.owner = ${var.config.team_name}"
  }
}

run "datadog_service_entity_test_name" {
  command = plan
  assert {
    condition     = yamldecode(datadog_software_catalog.datadog-software-catalog-service-front["test-api"].entity).metadata.name == "${var.application}-test-api"
    error_message = "Should be: metadata.displayName = ${var.application}-test-api"
  }
}

run "datadog_service_entity_test_parent" {
  command = plan
  assert {
    condition     = yamldecode(datadog_software_catalog.datadog-software-catalog-service-back["test-web-postgres"].entity).spec.componentOf[0] == "system:test-app-test-web"
    error_message = "Should be: spec.componentOf = system:test-app-test-web"
  }
}
