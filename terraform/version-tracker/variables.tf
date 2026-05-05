variable "platform_version" {
  type     = string
  nullable = false
}

variable "application" {
  type     = string
  nullable = false
}

variable "environment" {
  type     = string
  nullable = true
  default  = null
}

variable "service_name" {
  type     = string
  nullable = true
  default  = null
}

variable "pipeline_type" {
  type     = string
  nullable = true
  default  = null
}
