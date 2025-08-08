terraform {
  required_version = "~> 1.7"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5"
      configuration_aliases = [
        aws.domain,
      ]
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7.2"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4.2"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2.3"
    }
  }
}
