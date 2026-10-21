mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
    }
  }
}

run "creates_sqs_queue_with_no_subscriptions" {
  command = plan

  variables {
    config = {
      queue_name   = "test-queue"
      subscribe_to = []
    }
    application = "test-application"
    environment = "test-environment"
  }

  assert {
    condition     = aws_sqs_queue.this.name == "test-application-test-environment-test-queue"
    error_message = "Queue name should be test-application-test-environment-test-queue"
  }

  assert {
    condition     = length(aws_sns_topic_subscription.this) == 0
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

    application = "test-application"
    environment = "test-environment"
  }

  assert {
    condition     = aws_sqs_queue.this.name == "test-application-test-environment-test-queue"
    error_message = "Queue name should be test-application-test-environment-test-queue"
  }

  assert {
    condition     = length(aws_sns_topic_subscription.this) == 1
    error_message = "Queue length should be 1"
  }

  # Check that the subscription topic arn is the same as the topic arn as defined in the topic
  assert {
    condition     = aws_sns_topic_subscription.this["test-queue:example-topic-a"].topic_arn == "arn:aws:sns:eu-west-2:123456789012:example-topic-a"
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
    application = "test-application"
    environment = "test-environment"
  }

  assert {
    condition     = aws_sqs_queue.this.name == "test-application-test-environment-test-queue"
    error_message = "Queue name should be test-application-test-environment-test-queue"
  }

  assert {
    condition     = length(aws_sns_topic_subscription.this) == 3
    error_message = "Queue length should be 3"
  }

  # Check that the subscription to topic A is using the same topic arn as defined in topics
  assert {
    condition     = aws_sns_topic_subscription.this["test-queue:example-topic-a"].topic_arn == "arn:aws:sns:eu-west-2:123456789012:example-topic-a"
    error_message = "Subscription to Topic A should use the Topic A ARN"
  }

  assert {
    condition     = aws_sns_topic_subscription.this["test-queue:example-topic-b"].topic_arn == "arn:aws:sns:eu-west-2:123456789012:example-topic-b"
    error_message = "Subscription to Topic B should use the Topic B ARN"
  }

  assert {
    condition     = aws_sns_topic_subscription.this["test-queue:example-topic-c"].topic_arn == "arn:aws:sns:eu-west-2:123456789012:example-topic-c"
    error_message = "Subscription to Topic C should use the Topic C ARN"
  }
}

run "creates_sqs_queue_with_cross_account_subscription" {
  command = plan

  variables {
    config = {
      queue_name = "test-queue"
      subscribe_to = [
        {
          topic_name = "example-topic-a"
          account_id = "123456789013"
        },
        {
          topic_name = "example-topic-b"
        }
      ]
    }
    application = "test-application"
    environment = "test-environment"
  }

  assert {
    condition     = aws_sqs_queue.this.name == "test-application-test-environment-test-queue"
    error_message = "Queue name should be test-application-test-environment-test-queue"
  }

  assert {
    condition     = length(aws_sns_topic_subscription.this) == 2
    error_message = "Queue length should be 2"
  }

  # Check that the subscription to topic A is using the same topic arn as defined in topics
  assert {
    condition     = aws_sns_topic_subscription.this["test-queue:example-topic-a"].topic_arn == "arn:aws:sns:eu-west-2:123456789013:example-topic-a"
    error_message = "Subscription to Topic A should use the Topic A ARN and be a different account ID"
  }

  assert {
    condition     = aws_sns_topic_subscription.this["test-queue:example-topic-b"].topic_arn == "arn:aws:sns:eu-west-2:123456789012:example-topic-b"
    error_message = "Subscription to Topic B should use the Topic B ARN"
  }
}