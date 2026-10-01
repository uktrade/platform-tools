variable "environment" {
  type = string
}

variable "application" {
  type = string
}

variable "config" {
  type = object(
    {
      topic_name = string
    }
  )
}

# variable "topic_name" {
#   type        = string
#   description = "SNS topic name"
# }

variable "display_name" {
  type        = string
  default     = null
  description = "Display name for topic"
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Tags to apply to the SNS topic."
}

variable "allowed_sqs_subscriber_organization_id" {
  description = "AWS Organization ID allowed to subscribe SQS queues to this SNS topic (for example o-1234567890)."
  type        = string
  default     = null
}

# variable "queue_name" {
#   type        = string
#   description = "Queue name suffix."
# }

variable "delay_seconds" {
  description = "Seconds to delay delivery of new messages."
  type        = number
  default     = 0
}

variable "max_message_size" {
  description = "How long messages are retained in the source queue."
  type        = number
  default     = 262144
}

variable "visibility_timeout_seconds" {
  type        = number
  description = "Visibility timeout for messages."
  default     = 30
}

variable "message_retention_seconds" {
  type        = number
  description = "How long messages are retained in the queue."
  default     = 345600
}

variable "receive_wait_time_seconds" {
  type        = number
  description = "Long polling wait time."
  default     = 10
}

variable "create_dlq" {
  type        = bool
  description = "Whether to create a dead-letter queue."
  default     = true
}

variable "max_receive_count" {
  type        = number
  description = "Number of failed receives before moving message to DLQ."
  default     = 5
}

variable "dlq_message_retention_seconds" {
  type        = number
  description = "How long messages are retained in the DLQ."
  default     = 1209600
}

variable "sns_topic_subscriptions" {
  description = "SNS topics this SQS queue should subscribe to."
  type = map(object({
    topic_arn            = string
    raw_message_delivery = optional(bool, true)
    filter_policy        = optional(map(any))
    filter_policy_scope  = optional(string, "MessageAttributes")
  }))

  default = {}

  validation {
    condition = alltrue([
      for subscription in values(var.sns_topic_subscriptions) :
      contains(["MessageAttributes", "MessageBody"], try(subscription.filter_policy_scope, "MessageAttributes"))
    ])
    error_message = "sns_topic_subscriptions[*].filter_policy_scope must be either MessageAttributes or MessageBody."
  }
}
