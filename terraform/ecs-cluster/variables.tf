variable "application" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_name" {
  type = string
}

variable "alb_https_security_group_id" {
  type    = string
  default = null
}

variable "egress_rules" {
  type = list(object({
    to = object({
      cidr_blocks = set(string)
    })
  }))
  default = null
}