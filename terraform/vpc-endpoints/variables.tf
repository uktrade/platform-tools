variable "application" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_name" {
  type = string
}

variable "instances" {
  type = map(object({
    service_name = string
  }))
}
