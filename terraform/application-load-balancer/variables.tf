variable "application" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_name" {
  type = string
}

variable "dns_account_id" {
  type = string
}

variable "config" {
  type = object({
    domain_prefix                           = optional(string)
    additional_address_list                 = optional(list(string))
    slack_alert_channel_alb_secret_rotation = optional(string)
  })

  default = {}
}

variable "service_deployment_mode" {
  type = string
}

variable "name" {
  type = string
}
