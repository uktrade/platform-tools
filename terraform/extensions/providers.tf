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
  }
}
