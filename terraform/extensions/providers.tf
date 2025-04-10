# An 'alias' is required in some cases to help Terraform to run for_each loops inside of 
# extension modules that are themselves being called in a for_each loop. 
# Without the alias, Terraform forgets the provider on the next iteration and the plan will fail.

provider "aws" {
  alias = "domain"
  assume_role {
    role_arn = "arn:aws:iam::${local.dns_account_id}:role/environment-pipeline-assumed-role"
  }
}

provider "aws" {
  region = "us-east-1"
  alias  = "domain-cdn"
  assume_role {
    role_arn = "arn:aws:iam::${local.dns_account_id}:role/environment-pipeline-assumed-role"
  }
}

provider "datadog" {
  alias   = "ddog"
  api_key = data.aws_ssm_parameter.datadog_api_key.value
  app_key = data.aws_ssm_parameter.datadog_app_key.value
  api_url = "https://api.datadoghq.eu/"
}

terraform {
  required_version = "~> 1.7"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5"
      configuration_aliases = [
        aws.domain,
        aws.domain-cdn
      ]
    }
    datadog = {
      source                = "DataDog/datadog"
      version               = "3.57.0"
      configuration_aliases = [datadog.ddog]
    }
  }
}
