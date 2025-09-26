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

variable "env_config" {
  type = any
}

variable "config" {
  type = object({
    apply_immediately     = optional(bool)
    version               = number
    deletion_protection   = optional(bool)
    volume_size           = optional(number)
    iops                  = optional(number)
    snapshot_id           = optional(string)
    skip_final_snapshot   = optional(string)
    multi_az              = optional(bool)
    instance              = optional(string)
    storage_type          = optional(string)
    backup_retention_days = optional(number)
    database_copy = optional(list(
      object({
        from         = string
        to           = string
        from_account = optional(string)
        to_account   = optional(string)
        pipeline = optional(object({
          schedule = optional(string)
        }))
      })
    ))
  })
}
