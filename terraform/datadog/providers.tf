terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6"
    }
    datadog = {
      source                = "DataDog/datadog"
      version               = "3.78.0"
      configuration_aliases = [datadog.ddog]
    }
  }
}

