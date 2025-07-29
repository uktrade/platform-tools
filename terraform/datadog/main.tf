// Create the System (parent) component in DataDog Software Catalog
resource "datadog_software_catalog" "datadog-software-catalog-system" {
  provider = datadog.ddog
  for_each = var.config.services_to_monitor
  entity   = <<EOF
${local.api}
kind: system
metadata:
  name: ${var.application}-${each.key}
  links:
${local.doc}${local.repos}${local.dashboard}${local.contacts}${local.additionalowners}${local.team}
EOF
}

// Create the Service (child) component for the front-end services (e.g. iterate over web, api from the services_to_monitor variable)
resource "datadog_software_catalog" "datadog-software-catalog-service-front" {
  provider = datadog.ddog
  for_each = var.config.services_to_monitor
  entity   = <<EOF
${local.api}
kind: service
metadata:
  name: ${var.application}-${each.key}
  links:
${local.doc}${local.repos}${local.dashboard}${local.contacts}${local.additionalowners}${local.team}
spec:
  lifecycle: production
  tier: "1"
  type: ${contains(local.db_list, each.key) ? "db" : "web"}
  languages:
    - python
  componentOf: 
    - system:${var.application}-${each.key}
${local.fingerprint}
EOF
}

// Create the Service (child) components for the back-end services (e.g. iterate over redis, postgres, nginx from a local map variable)
resource "datadog_software_catalog" "datadog-software-catalog-service-back" {
  provider = datadog.ddog
  for_each = local.services_to_monitor_map
  entity   = <<EOF
${local.api}
kind: service
metadata:
  name: ${var.application}-${each.key}
  links:
${local.doc}${local.repos}${local.dashboard}${local.contacts}${local.additionalowners}${local.team}
spec:
  lifecycle: production
  tier: "1"
  type: ${contains(local.db_list, each.value.front_service) ? "db" : "web"}
  languages:
    - python
  componentOf: 
    - system:${var.application}-${each.value.front_service}
  dependsOn:
    - service:${var.application}-${each.value.front_service}
${local.fingerprint}
EOF
}

