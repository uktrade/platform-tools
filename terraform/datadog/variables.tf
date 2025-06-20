variable "application" {
  type = string
}

variable "environment" {
  type = string
}

variable "config" {
  type = object(
    {
      team_name           = string
      contact_name        = optional(string)
      contact_email       = optional(string)
      documentation_url   = string
      services_to_monitor = map(list(string))
    }
  )
}

variable "repos" {
  type = list(string)
}
