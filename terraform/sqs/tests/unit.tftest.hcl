mock_provider "aws" {}


run "creates_sqs_queue_with_no_subscriptions" {
  command = plan

  variables {
    config = {
      queue_name = "test-queue"
      subscribe_to = []
    }
    topics = {}
    application = "test-application"
    environment = "test-environment"
  }

  assert {
    condition = aws_sqs_queue.this.name == "test-queue"
    error_message = "Queue name should be test-queue"
  }
}

run "creates_sqs_queue_with_single_subscription" {
  command = plan

  variables {
    config = {
      queue_name = "test-queue"
      subscribe_to = [
        {
          topic_name = "example-topic-a"
        }
      ]
    }
    topics = {
      "example-topic-a" = {
      arn = "arn:aws:sns:eu-west-2:123456789012:topic-a"
      id = "example-topic-a-id"
      name = "example-topic-a-name"
      }
    }
    application = "test-application"
    environment = "test-environment"
  }

  assert {
    condition = length(aws_sns_topic_subscription.this) == 1
    error_message = "Queue length should be test-queue"
  }
}

