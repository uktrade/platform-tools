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

  assert {
    condition = length(aws_sns_topic_subscription.this) == 0
    error_message = "Queue length should be 0"
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
    condition = aws_sqs_queue.this.name == "test-queue"
    error_message = "Queue name should be test-queue"
  }

  assert {
    condition = length(aws_sns_topic_subscription.this) == 1
    error_message = "Queue length should be 1"
  }

  # Check that the subscription topic arn is the same as the topic arn as defined in the topic
  assert {
    condition = aws_sns_topic_subscription.this["test-queue:example-topic-a"].topic_arn == var.topics["example-topic-a"].arn
    error_message = "Subscription should use the expected topic ARN"
  }
}

run "creates_sqs_queue_with_three_subscription" {
  command = plan

  variables {
    config = {
      queue_name = "test-queue"
      subscribe_to = [
        {
          topic_name = "example-topic-a"
        },
        {
          topic_name = "example-topic-b"
        },
        {
          topic_name = "example-topic-c"
        }
      ]
    }
    topics = {
      "example-topic-a" = {
        arn = "arn:aws:sns:eu-west-2:123456789012:topic-a"
        id = "example-topic-a-id"
        name = "example-topic-a-name"
      },
      "example-topic-b" = {
        arn = "arn:aws:sns:eu-west-2:123456789012:topic-b"
        id = "example-topic-b-id"
        name = "example-topic-b-name"
      },
      "example-topic-c" = {
        arn = "arn:aws:sns:eu-west-2:123456789012:topic-c"
        id = "example-topic-c-id"
        name = "example-topic-c-name"
      }
    }
    application = "test-application"
    environment = "test-environment"
  }

  assert {
    condition = aws_sqs_queue.this.name == "test-queue"
    error_message = "Queue name should be test-queue"
  }

  assert {
    condition = length(aws_sns_topic_subscription.this) == 3
    error_message = "Queue length should be 3"
  }

  # Check that the subscription to topic A is using the same topic arn as defined in topics
  assert {
    condition = aws_sns_topic_subscription.this["test-queue:example-topic-a"].topic_arn == var.topics["example-topic-a"].arn
    error_message = "Subscription to Topic A should use the Topic A ARN"
  }

  assert {
    condition = aws_sns_topic_subscription.this["test-queue:example-topic-b"].topic_arn == var.topics["example-topic-b"].arn
    error_message = "Subscription to Topic B should use the Topic B ARN"
  }

  assert {
    condition = aws_sns_topic_subscription.this["test-queue:example-topic-c"].topic_arn == var.topics["example-topic-c"].arn
    error_message = "Subscription to Topic C should use the Topic C ARN"
  }
}

