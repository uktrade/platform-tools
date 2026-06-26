
variable "name" {
  default = null
  type    = string
}

variable "config" {
  type = object({
    domain               = string
    producer_account_id  = string
    producer_vpc_name    = string
    producer_application = string
    producer_environment = string
    consumer_account_id  = string
    consumer_cidr        = list(string)
  })
}
