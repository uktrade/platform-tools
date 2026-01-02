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

variable "has_vpc_endpoints" {
  type    = bool
  default = false
}

variable "vpc_endpoints_security_group_id" {
  type    = string
  default = null
  validation {
    condition     = !var.has_vpc_endpoints || var.vpc_endpoints_security_group_id != null
    error_message = "If has_vpc_endpoints is true, vpc_endpoints_security_group_id must be non-null"
  }
}


variable "egress_rules" {
  type = map(object({
    destination = object({
      cidr_blocks   = optional(set(string))
      vpc_endpoints = optional(bool)
      aws_cidr_blocks = optional(object({
        regions  = set(string)
        services = set(string)
        })
      )
    })
    protocol  = string
    from_port = number
    to_port   = number
    })
  )
  default = null
  validation {
    condition = var.egress_rules == null || alltrue([
      for rule in var.egress_rules :
      length([
        for key, val in rule.destination :
        key
        if val != null
      ]) == 1
    ])
    error_message = "All egress rules must set exactly one of: destination.cidr_blocks, destination.vpc_endpoints, destination.aws_cidr_blocks."
  }
}
