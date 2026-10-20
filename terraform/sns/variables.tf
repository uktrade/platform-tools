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
      allow_list = optional(list(string), [])
    }
  )
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Tags to apply to the SNS topic."
}
