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
  type = object(
    {
      allowed_account_ids = optional(list(string), [])
    }
  )
}
