locals {

# Local variables used to construct the metadata entity in datadog_software_catalog resource

  ## Datadog API / schema version to use for metadata
  api = <<EOF
apiVersion: v3
EOF

  ## Sections to add useful metadata to the services and system
  doc = <<EOF
    - name: Documentation
      type: doc
      url: ${var.config.documentation_url}
EOF

  ## Create repo metadata section(s)
  repos = var.repos == null ? "" : <<EOF
  %{for r in var.repos}
    - name: ${r}
      type: repo
      url: https://github.com/${r}
  %{endfor}
EOF

  ## Contact details
  contacts = <<EOF
  contacts:
    - name: ${var.config.contact_name}
      type: email
      contact: ${var.config.contact_email}
EOF

  ## Team name, which corresponds to the team name handle in Datadog
  team = <<EOF
  owner: ${var.config.team_name}
EOF

  ## Pipeline fingerprint
  fingerprint = <<EOF
datadog:
  pipelines:
    fingerprints:
      - SheHsDihoccN
EOF

  ## Create list of database types which can then be labelled as 'database' in the metadata
  db_list = ["postgres"]
  
# Map of 'services_to_monitor' to make it easier to iterate over when creating the datadog_software_catalog resources
  # use the coalesce function to provide a fallback value to use if backend service is null from platform-config.yml
  # i.e. this example where celery-worker is specified without backend services
  # services_to_monitor:
  #   web:
  #   - redis
  #   ...
  #   celery-worker:
  #   api:
  #   - nginx
  #   ....
  services_to_monitor_map = merge([
    for front_service, back_services in var.config.services_to_monitor : {
      for back_service in coalesce(back_services, []) : 
        "${front_service}-${back_service}" => {
          "back_service"   = back_service
          "front_service" = front_service
        }
    }
  ]...)

}


# Might need these blocks again at some point

#   # Dependency of back-end services such as redis, postgres etc on front end service (.e.g web, api)
#   depends_on = <<EOF
#   dependsOn:
#     - service:${var.application}-${var.environment}-web
# EOF

#   # Dependency of all services (child) to the system (parent)
#   component_of = <<EOF
#   componentOf: 
#     - system:${var.application}-${var.environment}-web
# EOF

#   # For all non-web services, they will have both of the above dependencies
#   both = "${local.component_of}${local.depends_on}"
