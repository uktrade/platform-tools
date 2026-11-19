terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6"
      configuration_aliases = [
        aws.domain,
        aws.domain-cdn,
        aws.us_east_1,
      ]
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}
