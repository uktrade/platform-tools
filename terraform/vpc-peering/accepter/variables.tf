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
    source_vpc_id             = optional(string)
    target_hosted_zone_ids    = optional(list(string))
    accept_remote_dns         = bool
    security_group_map        = optional(map(string))
    ecs_security_groups = optional(map(object({
      port        = string
      application = string
      environment = string
    })))
  })
}
