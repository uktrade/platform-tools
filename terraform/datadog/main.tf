locals {
# Dependency of back-end services such as redis, postgres etc on web
  depends_on = <<EOF
  dependsOn:
    - service:${var.application}-${var.environment}-web
EOF

# Dependency of all services (child) to the system (parent)
  component_of = <<EOF
  componentOf: 
    - system:${var.application}-${var.environment}
EOF

# For all non-web services, they will have both of the above dependencies
  both = "${local.component_of}${local.depends_on}"

# Sections to add useful metadata to the services and system
  doc = <<EOF
    - name: Documentation
      type: doc
      url: ${var.config.documentation_url}
EOF

  repo = var.repository == null ? "" : <<EOF
    - name: Repository
      type: repo
      url: https://github.com/${var.repository}
EOF

  contacts = <<EOF
  contacts:
    - name: ${var.config.contact_name}
      type: email
      contact: ${var.config.contact_email}
EOF

  team = <<EOF
  owner: ${var.config.team_name}
EOF

# Create list of database types which can then be labelled as 'database' in the metadata
  db_list = ["postgres"]

}

// Create the System (parent) component in DataDog Software Catalog
resource "datadog_software_catalog" "datadog-software-catalog-system" {
  provider = datadog.ddog
  entity   = <<EOF
apiVersion: v3
kind: system
metadata:
  name: ${var.application}-${var.environment}
  links:
${local.doc}${local.repo}${local.contacts}${local.team}
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
${local.doc}${local.repo}${local.contacts}${local.team}
spec:
  lifecycle: production
  tier: "1"
  type: ${contains(local.db_list, each.value) ? "db" : "web"}
${each.value == "web" ? local.component_of : local.both}
  languages:
    - python
datadog:
  pipelines:
    fingerprints:
      - SheHsDihoccN
EOF
}
