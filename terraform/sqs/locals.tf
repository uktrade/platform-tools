locals {
  #take every subscription and set source_environment = current environment, which it will be in most cases,
  #unless platform-config explicitly states a different source_environment for the SNS topic

    # This is the config in platform-config
    # demodjango-sqs:
    # type: sqs
    # environments:
    #   daveg:
    #     subscribe_to: 
    #     - topic_name: sns-topic-a
    #       source_environment: daveg #- we could assume that if no env given, then use this one
    #     - topic_name: sns-topic-c
    #       source_environment: jayesh

    # This variable contains each topic_name and source_env that we want this SQS to subscribe to
    # variable "config" {
    #   type = object({
    #     subscribe_to = list(object({
    #       topic_name         = string
    #       source_environment = optional(string) #make this optional as in most cases it would be the same as the running environment, and use a local to set it as such
    #     }))
    #   })
    # }

    # like this:
    # [
    #   {
    #     topic_name         = "sns-topic-a"
    #     source_environment = "daveg"
    #   }
    # ]

    # or like this, if a source_environment isn't specified
    # [
    #   {
    #     topic_name         = "sns-topic-b"
    #     source_environment = null
    #   }
    # ]

  # subscriptions = {                            #        
  #   for sub in var.config.subscribe_to :       # each subscribe_to object
  #     sub.topic_name => {                      # make a map with topic_name as the key
  #       topic_name = sub.topic_name            # assign the value to topic_name, which will be the 
  #                                              # 'topic_name' from the subscribe_to section, e.g. 
  #                                              # topic_name         = "sns-topic-a"
  #       source_environment = (                 # as a key called source_environment to this object
  #         sub.source_environment != null       # if there is a source_environment provided
  #         ? sub.source_environment             # then assign that value to source_environment in this object
  #         : var.environment                    # else, assume its their own local environment
  #       )
  #     }
  # }

  # simpler way, now key is the topic_name, and the value is the source_environment
  # subscriptions = {
  #   for sub in var.config.subscribe_to :
  #     sub.topic_name => {
  #       source_environment = (
  #         sub.source_environment != null
  #         ? sub.source_environment
  #         : var.environment
  #       )
  #     }
  # }

  subscriptions = {
    for sub in coalesce(var.config.subscribe_to, null, []) : # add a coalesce in case subscribe_to is null, then change it to an empty list and the for loop skips over it
      sub.topic_name => {
        source_environment = (
          sub.source_environment != null
          ? sub.source_environment
          : var.environment
        )
      }
  }

  # if the environment in platform-config where the SNS topics to subscribe to are defined,
  # and the env we are running in are NOT the same, then put them into a 'remote' variable 
  # This is for when we need to look up SNS Topic that aren't managed by this terraform,
  # e.g.
  #   data "aws_sns_topic" "remote" {
  #     for_each = local.remote_subscriptions
  #     name = "${var.application}-${each.value.source_environment}-${each.key}"
  #   }
  remote_subscriptions = {
    for k, v in local.subscriptions :
      k => v
      if v.source_environment != var.environment
  }

}
