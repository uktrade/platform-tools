variable "name" {
  default = null
  type    = string
}

variable "config" {
  type = object({
    vpc_peering_connection_id = string
    requester_vpc_name        = string
    accepter_vpc              = string
    requester_subnet          = string
    security_group_map        = optional(map(string))
    source_vpc_id             = optional(string)
    target_hosted_zone_id     = optional(list(string))
    accept_remote_dns         = bool
  })
}
