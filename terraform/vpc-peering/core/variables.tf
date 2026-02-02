variable "vpc_id" {
  type = string
}

variable "subnet" {
  type = string
}

variable "vpc_peering_connection_id" {
  type = string
}

variable "security_group_map" {
  type = map(string)
}

variable "vpc_name" {
  type = string
}

variable "source_vpc_id" {
  type = string
}

# A list is needed to simultaneously support new and old CloudMap hosted zones during the AWS Copilot removal
variable "target_hosted_zone_ids" {
  type = list(string)
}

variable "accept_remote_dns" {
  type     = bool
  nullable = false
}
