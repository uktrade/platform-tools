variable "vpc_id" {
  type = string
}

variable "subnet" {
  type = string
}

variable "vpc_peering_connection_id" {
  type = string
}

# Note: Only for applications deployed using AWS Copilot. Otherwise, use var.ecs_security_groups below.
variable "security_group_map" {
  type = map(string)
}

# Note: Only for applications that are not deployed using AWS Copilot.
variable "ecs_security_groups" {
  type = map(object({
    port        = string
    application = string
    environment = string
  }))
  description = "ECS security group(s) that will allow ingress VPC peering traffic into the destination (remote) AWS account."
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
