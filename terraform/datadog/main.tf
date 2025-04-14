// Create the System (parent) component in DataDog Software Catalog
resource "datadog_software_catalog" "datadog-software-catalog-system" {
  provider = datadog.ddog
  entity   = <<EOF
apiVersion: v3
kind: system
metadata:
  name: ${var.application}-${var.environment}
  links:
    - name: Documentation
      type: doc
      url: ${var.config.documentation_url}
  contacts:
    - name: ${var.config.contact_name}
      type: email
      contact: ${var.config.contact_email}
  owner: ${var.config.team_name}
EOF
}

// Create the Service (child) component in DataDog Software Catalog
resource "datadog_software_catalog" "datadog-software-catalog-service" {
  provider = datadog.ddog
  for_each = toset(var.config.services_to_monitor)
  entity   = <<EOF
apiVersion: v3
kind: service
metadata:
  name: ${var.application}-${var.environment}-${each.value}
  links:
    - name: Documentation
      type: doc
      url: ${var.config.documentation_url}
  contacts:
    - name: ${var.config.contact_name}
      type: email
      contact: ${var.config.contact_email}
  owner: ${var.config.team_name}
spec:
  lifecycle: production
  tier: "1"
  type: web
  componentOf: 
    - system:${var.application}-${var.environment}
  languages:
    - python
datadog:
  pipelines:
    fingerprints:
      - SheHsDihoccN
EOF
}
