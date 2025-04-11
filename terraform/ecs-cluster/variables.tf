variable "application" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_name" {
  type = string
}

variable "services" {
  type = any
}

variable "s3_config" {
  type = any
}
