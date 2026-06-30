
variable "name" {
  default = null
  type    = string
}

variable "healthcheck-port" {
  default     = 8080
  type        = number
  description = "Port where healthcheck will call"
}
variable "config" {
  type = object({
    domain               = string
    producer_account_id  = string
    producer_vpc_name    = string
    producer_application = string
    producer_environment = string
    consumer_account_id  = string
    consumer_cidr        = list(string)
  })

  validation {
    condition = alltrue([
      for cidr in var.config.consumer_cidr : can(cidrhost(cidr, 0))
    ])
    error_message = "All should be valid cidr block."
  }

  validation {
    condition     = !contains(var.config.consumer_cidr, "0.0.0.0/0")
    error_message = "Must not contain 0.0.0.0/0"
  }
}
