terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6"
    }
    github = {
      source  = "integrations/github"
      version = "~> 6"
    }
  }
}
