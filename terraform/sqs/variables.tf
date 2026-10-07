variable "environment" {
  type = string
}

variable "application" {
  type = string
}

# variable "config" {
#   type = object(
#     {
#       #queue_name = string
#       subscribe_to = set(string)
#     }
#   )
# }

variable "config" {
  type = object({
    queues = list(object({
      queue_name = string
      subscribe_to = optional(list(object({
        topic_name = string
        #source_environment = optional(string)
      })))

      visibility_timeout_seconds = optional(number, 30)

      dead_letter_queue = optional(object({
        enbaled           = optional(bool, true)
        max_receive_count = optional(number, 5)
      }))
    }))
  })
}


variable "topics" {
  type = map(object({
    arn  = string
    id   = string
    name = string
  }))
}

# variable "topic_arn" {
#   type        = any
#   description = "SNS topic arn"
# }

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

variable "dlq_message_retention_seconds" {
  type        = number
  description = "How long messages are retained in the DLQ."
  default     = 1209600
}
