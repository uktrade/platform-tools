variable "application" {
  type = string
}

variable "environment" {
  type = string
}

variable "database_name" {
  type = string
}

variable "tasks" {
  type = list(object({
    from         = string
    to           = string
    from_account = optional(string)
    to_account   = optional(string)
    pipeline     = optional(object({}))
  }))
}
