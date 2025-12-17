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

variable "vpc_endpoints_security_group_id" {
  type    = string
  default = null
}

variable "regions" {
  type = string
}

variable "egress_rules" {
  type = list(object({
    to = object({
      cidr_blocks   = optional(set(string))
      vpc_endpoints = optional(bool)
      aws_cidr_blocks = optional(object({
        regions = set(string)
        services = set(string)
      })))
    })
    protocol  = string
    from_port = number
    to_port   = number
    
  }))
  default = null
  validation {
    condition = var.egress_rules == null || alltrue([
      for rule in var.egress_rules :
      length([
        for key, val in rule.to :
        key
        if val != null
      ]) == 1
    ])
    error_message = "All egress rules must set exactly one of: to.cidr_blocks, to.vpc_endpoints."
  }
}