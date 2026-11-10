variable "environment" {
  type = string
}

variable "application" {
  type = string
}

variable "name" {
  type = string
}

variable "config" {
  type = object({
    visibility_timeout_seconds = optional(number, 30)
    filter_policy_scope        = optional(string)
    filter_policy              = optional(any)
    raw_message_delivery       = optional(bool, false)
    delay_seconds              = optional(number, 0)
    max_message_size           = optional(number, 262144)
    message_retention_seconds  = optional(number, 345600)
    receive_wait_time_seconds  = optional(number, 10)
    subscribe_to = optional(list(object({
      topic_name  = string
      account_id  = optional(string)
      application = optional(string)
      environment = optional(string)
    })), [])

    dead_letter_queue = optional(object({
      enabled                   = optional(bool, true)
      max_receive_count         = optional(number, 5)
      message_retention_seconds = optional(number, 1209600)
    }), { "enabled" : true, "max_receive_count" : 5 })
  })
}
