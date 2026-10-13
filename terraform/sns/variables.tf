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
