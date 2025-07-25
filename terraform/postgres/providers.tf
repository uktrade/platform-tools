terraform {
  required_version = "~> 1.7"
  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7.1"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6.0"
    }
  }
}
