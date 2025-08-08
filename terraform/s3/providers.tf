terraform {
  required_version = "~> 1.7"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6"
      configuration_aliases = [
        aws.domain-cdn,
      ]
    }
  }
}
