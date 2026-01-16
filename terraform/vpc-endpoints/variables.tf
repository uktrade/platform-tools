variable "application" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_name" {
  type = string
}

variable "endpoint_definitions" {
  type = map(object({
    service_name = string
  }))
}
