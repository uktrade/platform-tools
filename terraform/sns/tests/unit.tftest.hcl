mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
    }
  }

  # Mocks the AWS Organization Root ID and Organization ID
  mock_data "aws_organizations_organization" {
    defaults = {
      id = "o-123456789h"
      roots = [
        {
          id   = "r-ab12"
          name = "Root"
          arn  = "arn:aws:organizations::123456789012:root/o-123456789h/r-ab12"
        }
      ]
    }
  }

  # Mocks the list of Child OUs sitting under the Root
  mock_data "aws_organizations_organizational_units" {
    defaults = {
      children = [
        {
          id   = "ou-ab12-34567890"
          name = "Production"
          arn  = "arn:aws:organizations::123456789012:ou/o-123456789h/ou-ab12-34567890"
        }
      ]
    }
  }

  mock_data "aws_organizations_entity_path" {
    defaults = {
      path = "o-123456789h/r-ab12/ou-ghi0-awsccccc/"
    }
  }
}

run "creates_single_sns_topic" {
  command = plan

  variables {
    config = {
      topic_name = "test-topic"
    }
    application = "test-application"
    environment = "test-environment"
  }

  assert {
    condition     = aws_sns_topic.this.name == "test-application-test-environment-test-topic"
    error_message = "Topic name should include application, environment and topic name"
  }
}