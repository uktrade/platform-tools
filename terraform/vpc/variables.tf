variable "arg_name" {
  default = null
  type    = string
}

# variable "arg_config" {
#   default = null
#   type    = any
# }

variable "arg_config" {
  type = object({
    cidr         = string
    nat_gateways = any
    az_map       = any
    region       = optional(string)
  })
}
