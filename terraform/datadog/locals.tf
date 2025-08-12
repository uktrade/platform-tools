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
  ## Both name and email are required for this block, so don't add if either are missing from platform-config.yml
  ## This supports the 'old' way of setting email contact in platform-config.yml like this:
  #contact_name: DBT Platform Engineers, Dave Glover
  #contact_email: dbt-platform-engineers@digital.trade.gov.uk, david.glover@digital.trade.gov.uk
  contact_name  = var.config.contact_name != null ? split(",", var.config.contact_name) : null
  contact_email = var.config.contact_email != null ? split(",", var.config.contact_email) : null
  contacts      = var.config.contact_name == null || var.config.contact_email == null ? "" : <<EOF
  %{for k, v in local.contact_name}
    - name: ${v}
      type: email
      contact: ${local.contact_email[k]}
  %{endfor}
EOF

  ## This supports the 'new' way of setting contacts in platform-config.yml which replicates the Datadog schema
  ## https://github.com/DataDog/schema/blob/b76ed2b7681cd7d681520aa8760e5b09c347865b/service-catalog/v3/metadata.schema.json
  # contacts:
  #  - name: DBT Platform Engineers
  #    type: email
  #    contact: dbt-platform-engineers@digital.trade.gov.uk
  #  - name: Dave Glover
  #    type: email
  #    contact: david.glover@digital.trade.gov.uk
  #  - name: platform-squad-3
  #    type: slack
  #    contact: https://ditdigitalteam.slack.com/archives/C08FASZ72LS
  #  - name: DBT Platform Team Intranet Page
  #    type: link
  #    contact: https://workspace.trade.gov.uk/teams/dbt-platform-team/?sub_view=people
  contact_check = try(var.config.contacts, null)
  contacts_new  = <<EOF
  %{if local.contact_check != null && var.config.contact_name != null}
    %{for k, v in var.config.contacts}
    - name: ${v.name}
      type: ${v.type}
      contact: ${v.contact}
    %{endfor}
  %{endif}
EOF

  ## Set SRE to be the additionalOwners as a workaround to not being able to specify an on-call team that is different than the owner team
  description_check = var.config.description == null ? "${var.application} application" : var.config.description
  description       = <<EOF
  description: ${local.description_check}
EOF

  ## Set SRE to be the additionalOwners as a workaround to not being able to specify an on-call team that is different than the owner team
  additionalowners = <<EOF
  additionalOwners:
    - name: sre
      type: On-Call Team
EOF

  ## Team name, which corresponds to the team name handle in Datadog
  team = <<EOF
  owner: ${var.config.team_name}
EOF

  ## Link to the standard dashboard 
  dashboard = <<EOF
    - name: DBT Application Overview v2
      type: dashboard
      url: https://dbt.datadoghq.eu/dashboard/nwy-xqe-yv3/dbt-application-overview-v2?fromUser=false&refresh_mode=sliding&tpl_var_copilot-application%5B0%5D=${var.application}
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
        "back_service"  = back_service
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
