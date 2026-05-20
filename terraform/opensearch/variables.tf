variable "application" {
  type = string
}

variable "environment" {
  type = string
}

variable "name" {
  type = string
}

variable "vpc_name" {
  type = string
}

variable "config" {
  type = object({
    engine                            = string,
    instances                         = number,
    instance                          = string,
    volume_size                       = number,
    enable_ha                         = bool,
    ebs_volume_type                   = optional(string)
    ebs_throughput                    = optional(number)
    index_slow_log_retention_in_days  = optional(number)
    search_slow_log_retention_in_days = optional(number)
    es_app_log_retention_in_days      = optional(number)
    audit_log_retention_in_days       = optional(number)
    password_special_characters       = optional(string)
    urlencode_password                = optional(bool)
    master                            = optional(bool) # Keeping for now to avoid a breaking change. This is deprecated and will need to be removed in a future update.
    # NOTE: allows access to Opensearch from outwith the account
    external_user_access = optional(map(object({
      index             = bool,
      read              = bool,
      write             = bool,
      cyber_sign_off_by = string
    })))
  })

  validation {
    condition     = contains(["standard", "gp2", "gp3", "io1", "io2", "sc1", "st1"], coalesce(var.config.ebs_volume_type, "gp2"))
    error_message = "var.config.ebs_volume_type must be one of: standard, gp2, gp3, io1, io2, sc1 or st1"
  }
}
