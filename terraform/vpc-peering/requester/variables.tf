
variable "name" {
  default = null
  type    = string
}

variable "config" {
  type = object({
    accepter_account_id   = string
    accepter_vpc          = string
    accepter_vpc_name     = string
    accepter_region       = optional(string)
    accepter_subnet       = string
    requester_vpc         = string
    security_group_map    = optional(map(string))
    source_vpc_id         = optional(string)
    target_hosted_zone_id = optional(list(string))
    accept_remote_dns     = optional(bool)
  })
}
