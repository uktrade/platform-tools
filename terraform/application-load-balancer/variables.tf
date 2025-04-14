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
    env_root                                = optional(string)
    cdn_domains_list                        = optional(map(list(string)))
    additional_address_list                 = optional(list(string))
    slack_alert_channel_alb_secret_rotation = optional(string)
  })

  default = {}

  validation {
    condition = var.config.cdn_domains_list == null ? true : alltrue([
      for k, v in var.config.cdn_domains_list : ((length(k) <= 63) && (length(k) >= 3))
    ])
    error_message = "Items in cdn_domains_list should be between 3 and 63 characters long."
  }
}
