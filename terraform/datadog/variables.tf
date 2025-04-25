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
      contact_name        = string
      contact_email       = string
      documentation_url   = string
      services_to_monitor = list(string)
    }
  )
}

variable "repository" {
  type = string
}

