variable "environment" {
  type = string
}

variable "application" {
  type = string
}

variable "config" {
  type = object(
    {
      topic_name = set(string)
    }
  )
}

# variable "topic_name" {
#   type        = string
#   description = "SNS topic name"
# }

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Tags to apply to the SNS topic."
}

variable "allowed_sqs_subscriber_organization_id" {
  description = "AWS Organization ID allowed to subscribe SQS queues to this SNS topic (for example o-1234567890)."
  type        = string
  default     = "CHANGE ME!!"
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
