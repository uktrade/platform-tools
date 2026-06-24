variable "application" {
  type = string
}

variable "environment" {
  type = string
}

variable "database_name" {
  type = string
}

variable "deploy_repository" {
  type = string
}

variable "task" {
  type = object({
    from         = string
    to           = string
    from_account = string
    to_account   = string
    pipeline = optional(object({
      schedule = optional(string)
    }))
  })
}

variable "pinned_version" {
  type    = string
  default = null
}
