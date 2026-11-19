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
      subscribe_to = []
    }
    application = "test-application"
    environment = "test-environment"
    name        = "test-queue"
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
      subscribe_to = [
        {
          topic_name = "example-topic-a"
        }
      ]
    }

    application = "test-application"
    environment = "test-environment"
    name        = "test-queue"
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
    condition     = aws_sns_topic_subscription.this["test-queue:test-application/test-environment/example-topic-a"].topic_arn == "arn:aws:sns:eu-west-2:123456789012:test-application-test-environment-example-topic-a"
    error_message = "Subscription should use the expected topic ARN"
  }
}

run "creates_sqs_queue_with_three_subscription" {
  command = plan

  variables {
    config = {
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
    name        = "test-queue"
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
    condition     = aws_sns_topic_subscription.this["test-queue:test-application/test-environment/example-topic-a"].topic_arn == "arn:aws:sns:eu-west-2:123456789012:test-application-test-environment-example-topic-a"
    error_message = "Subscription to Topic A should use the Topic A ARN"
  }

  assert {
    condition     = aws_sns_topic_subscription.this["test-queue:test-application/test-environment/example-topic-b"].topic_arn == "arn:aws:sns:eu-west-2:123456789012:test-application-test-environment-example-topic-b"
    error_message = "Subscription to Topic B should use the Topic B ARN"
  }

  assert {
    condition     = aws_sns_topic_subscription.this["test-queue:test-application/test-environment/example-topic-c"].topic_arn == "arn:aws:sns:eu-west-2:123456789012:test-application-test-environment-example-topic-c"
    error_message = "Subscription to Topic C should use the Topic C ARN"
  }
}

run "creates_sqs_queue_with_cross_account_subscription" {
  command = plan

  variables {
    config = {
      subscribe_to = [
        {
          topic_name  = "example-topic-a"
          account_id  = "123456789013"
          application = "way-over"
          environment = "yonder"
        },
        {
          topic_name = "example-topic-b"
        }
      ]
    }
    application = "test-application"
    environment = "test-environment"
    name        = "test-queue"
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
    condition     = aws_sns_topic_subscription.this["test-queue:way-over/yonder/example-topic-a"].topic_arn == "arn:aws:sns:eu-west-2:123456789013:way-over-yonder-example-topic-a"
    error_message = "Subscription to Topic A should use the Topic A ARN and be a different account ID"
  }

  assert {
    condition     = aws_sns_topic_subscription.this["test-queue:test-application/test-environment/example-topic-b"].topic_arn == "arn:aws:sns:eu-west-2:123456789012:test-application-test-environment-example-topic-b"
    error_message = "Subscription to Topic B should use the Topic B ARN"
  }
}

run "creates_sqs_queue_with_dlq" {
  command = plan

  variables {
    config = {
      subscribe_to = []
      dead_letter_queue = {
        enabled = true
      }
    }

    application = "test-application"
    environment = "test-environment"
    name        = "test-queue"
  }

  assert {
    condition     = aws_sqs_queue.this.name == "test-application-test-environment-test-queue"
    error_message = "Queue name should be test-application-test-environment-test-queue"
  }

  assert {
    condition     = aws_sqs_queue.dlq[0].name == "test-application-test-environment-test-queue-dlq"
    error_message = "Should create a DLQ named the same as source queue with -dlq suffix"
  }
}

run "creates_sqs_queue_with_single_subscription_and_filter_policy" {
  command = plan

  variables {
    config = {
      filter_policy_scope = "MessageBody"

      filter_policy = {
        message = {
          part1 = ["123"]
          part2 = ["abc"]
        }
      }

      raw_message_delivery = true
      subscribe_to = [
        {
          topic_name = "example-topic-a"
        }
      ]
    }

    application = "test-application"
    environment = "test-environment"
    name        = "test-queue"
  }

  assert {
    condition     = aws_sqs_queue.this.name == "test-application-test-environment-test-queue"
    error_message = "Queue name should be test-application-test-environment-test-queue"
  }

  assert {
    condition     = aws_sns_topic_subscription.this["test-queue:test-application/test-environment/example-topic-a"].raw_message_delivery == true
    error_message = "raw_message_delivery should be true"
  }

  assert {
    condition     = aws_sns_topic_subscription.this["test-queue:test-application/test-environment/example-topic-a"].filter_policy_scope == "MessageBody"
    error_message = "filter_policy_scope should be MessageBody"
  }

  assert {
    condition = aws_sns_topic_subscription.this["test-queue:test-application/test-environment/example-topic-a"].filter_policy == jsonencode({
      message = {
        part1 = ["123"]
        part2 = ["abc"]
      }
    })

    error_message = "Filter policy was not configured correctly"
  }
}
