mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
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