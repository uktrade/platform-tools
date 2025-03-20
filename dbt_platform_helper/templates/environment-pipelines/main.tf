# {% extra_header %}
# {% version_info %}
locals {
  platform_config    = yamldecode(file("../../../platform-config.yml"))
  all_pipelines      = local.platform_config["environment_pipelines"]
  pipelines          = { for pipeline, config in local.platform_config["environment_pipelines"] : pipeline => config if config.account == "{{ aws_account }}" }
  environment_config = local.platform_config["environments"]
}

provider "aws" {
  region                   = "eu-west-2"
  profile                  = "{{ aws_account }}"
  alias                    = "{{ aws_account }}"
  shared_credentials_files = ["~/.aws/config"]
}

terraform {
  required_version = "{{ terraform_version }}"
  backend "s3" {
    bucket         = "terraform-platform-state-{{ aws_account }}"
    key            = "tfstate/application/{{ application }}-pipelines.tfstate"
    region         = "eu-west-2"
    encrypt        = true
    kms_key_id     = "alias/terraform-platform-state-s3-key-{{ aws_account }}"
    dynamodb_table = "terraform-platform-lockdb-{{ aws_account }}"
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "{{ aws_provider_version }}"
    }
  }
}


module "environment-pipelines" {
  source = "git::https://github.com/uktrade/platform-tools.git//terraform/environment-pipelines?depth=1&ref={{ platform_helper_version }}"

  for_each = local.pipelines

  application         = "{{ application }}"
  pipeline_name       = each.key
  repository          = "{{ deploy_repository }}"

  environments        = each.value.environments
  all_pipelines       = local.all_pipelines
  environment_config  = local.environment_config
  branch              = {% if deploy_branch %}"{{ deploy_branch }}"{% else %}each.value.branch{% endif %}
  slack_channel       = each.value.slack_channel
  trigger_on_push     = each.value.trigger_on_push
  pipeline_to_trigger = lookup(each.value, "pipeline_to_trigger", null)
}
