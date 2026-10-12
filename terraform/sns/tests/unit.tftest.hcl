mock_provider "aws" {}

run "creates_single_sns_topic" {
  command = plan

  variables {
    config = {
      topic_name = ["test-topic"]
    }
    application = "test-application"
    environment = "test-environment"
  }

  assert {
    condition     = aws_sns_topic.this["test-topic"].name == "test-application-test-environment-test-topic"
    error_message = "Topic name should include application, environment and topic name"
  }

  assert {
    condition = output.topics["test-topic"].name == "test-application-test-environment-test-topic"
    error_message = "Output should contain the expected topic name"
  }
}

run "creates_three_sns_topics" {
  command = plan

  variables {
    config = {
      topic_name = ["test-topic-one", "test-topic-two", "test-topic-three"]
    }
    application = "test-application"
    environment = "test-environment"
  }

  assert {
    condition     = aws_sns_topic.this["test-topic-one"].name == "test-application-test-environment-test-topic-one"
    error_message = "Topic name should include application, environment and topic name"
  }

  assert {
    condition     = aws_sns_topic.this["test-topic-two"].name == "test-application-test-environment-test-topic-two"
    error_message = "Topic name should include application, environment and topic name"
  }

  assert {
    condition     = aws_sns_topic.this["test-topic-three"].name == "test-application-test-environment-test-topic-three"
    error_message = "Topic name should include application, environment and topic name"
  }
}