locals {
  # To handle multiple SQS queues, platform-config has a key called 'queues'
  # so that we can store the subsequent key/vals in an iterable object
    # demodjango-sqs:
    # type: sqs
    # environments:
    #   daveg:
    #     queues:
    #       - queue_name: demodjango-daveg-sqs-queue-a
    #         subscribe_to:
    #           - topic_name: sns-topic-a
    #       - queue_name: demodjango-daveg-sqs-queue-b
    #         subscribe_to:
    #           - topic_name: sns-topic-b
  queues = {
    for q in var.config.queues :
    q.queue_name => q
  }
  
  # Take every subscription and set source_environment = current environment, which it will be in most cases,
  # unless platform-config explicitly states a different source_environment for the SNS topic
  subscriptions = merge([
    for queue in var.config.queues : {
      #for sub in coalesce(queue.subscribe_to, []) :
      for sub in coalesce(try(queue.subscribe_to, null), []) : #subscribe_to is now optional
      "${queue.queue_name}:${sub.topic_name}" => {
        queue_name         = queue.queue_name
        topic_name         = sub.topic_name
        # source_environment = coalesce(
        #   sub.source_environment,
        #   var.environment
        # )
      }
    }
  ]...)

  # if the environment in platform-config where the SNS topics to subscribe to are defined,
  # and the env we are running in are NOT the same, then put them into a 'remote' variable 
  # This is for when we need to look up SNS Topic that aren't managed by this terraform,
  # e.g.
  # data "aws_sns_topic" "remote" {
  #   for_each = local.remote_subscriptions
  #   name = "${var.application}-${each.value.source_environment}-${each.key}"
  # }
  remote_subscriptions = {
    for k, v in local.subscriptions :
    v.topic_name => v
    #if v.source_environment != var.environment
  }

}
