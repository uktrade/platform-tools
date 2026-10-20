variable "environment" {
  type = string
}

variable "application" {
  type = string
}

variable "config" {
  type = object({
    queue_name = string

    visibility_timeout_seconds = optional(number, 30)

    subscribe_to = optional(list(object({
      topic_name = string
      account_id = optional(string)
    })), [])

    dead_letter_queue = optional(object({
      enabled           = optional(bool, true)
      max_receive_count = optional(number, 5)
    }), { "enabled" : true, "max_receive_count" : 5 })
  })
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Tags to apply to the SNS topic."
}

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
