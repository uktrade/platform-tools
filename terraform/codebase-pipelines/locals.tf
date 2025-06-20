locals {
  tags = {
    application         = var.application
    copilot-application = var.application
    managed-by          = "DBT Platform - Terraform"
  }

  account_region = "${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}"

  ecr_name                    = "${var.application}/${var.codebase}"
  private_repo_url            = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com"
  is_additional_repo_public   = var.additional_ecr_repository != null ? strcontains(var.additional_ecr_repository, "public.ecr.aws") : false
  additional_ecr_url          = var.additional_ecr_repository != null ? local.is_additional_repo_public ? var.additional_ecr_repository : "${local.private_repo_url}/${var.additional_ecr_repository}" : null
  repository_url              = coalesce(local.additional_ecr_url, "${local.private_repo_url}/${local.ecr_name}")
  additional_private_repo_arn = var.additional_ecr_repository != null && !local.is_additional_repo_public ? "arn:aws:ecr:${local.account_region}:repository/${var.additional_ecr_repository}" : ""

  pipeline_branches = distinct([
    for pipeline in var.pipelines : pipeline.branch if lookup(pipeline, "branch", null) != null
  ])

  tagged_pipeline = length([for pipeline in var.pipelines : true if lookup(pipeline, "tag", null) == true]) > 0

  base_env_config = {
    for name, config in var.env_config : name => {
      account : lookup(lookup(lookup(merge(lookup(var.env_config, "*", {}), config), "accounts", {}), "deploy", {}), "id", {}),
      dns_account : lookup(lookup(lookup(merge(lookup(var.env_config, "*", {}), config), "accounts", {}), "dns", {}), "id", {})
    } if name != "*"
  }

  deploy_account_ids = distinct([for env in local.base_env_config : env.account])
  
  dns_account_ids = distinct([for env in local.base_env_config : env.dns_account])
  dns_account_assumed_roles = [for id in local.dns_account_ids : "arn:aws:iam::${id}:role/environment-pipeline-assumed-role"]

  environments_requiring_cache_invalidation = distinct([for d in var.cache_invalidation.domains : d.environment])
  cache_invalidation_enabled = length(local.environments_requiring_cache_invalidation) > 0
  pipeline_map = {
    for id, val in var.pipelines : id => merge(val, {
      environments : [
        for name, env in val.environments : merge(env, merge(
          lookup(local.base_env_config, env.name, {}),
          {
            requires_cache_invalidation: contains(local.environments_requiring_cache_invalidation, env.name)
          }
        ))
      ],
    })
  }

  cache_invalidation_map = tomap({
    for env in local.environments_requiring_cache_invalidation : env => {
      for domain, data in var.cache_invalidation.domains : domain => data.paths if data.environment == env
    }
  })

  # "dev":
  #   {"www.domain.com": ["a","b"],
  #   "www.domain2.com": ["a", "b"]}
  # "prod":


  # TODO
  # output pipeline_map to see what shape it is and how we might adapt it to hold caching information
  # What we need:


  services = sort(flatten([
    for run_group in var.services : [for service in flatten(values(run_group)) : service]
  ]))

  service_order_list = flatten([
    for index, group in var.services : [
      for key, services in group : [
        for sorted_service in local.services : [
          for service in services : {
            name  = service
            order = index + 1
          } if service == sorted_service
        ]
      ]
    ]
  ])

}
