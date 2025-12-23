variable "args" {
  type = object({
    application = string,
    services    = any,
    env_config  = any
    # env_config = {
    #.  staging = {
    #.    network = {
    #.      vpc_endpoints = { ... }
    #.      egress_rules = { ... }
    #.    }
    #   },
    #.  prod = { ... }
    # }
  })
}

variable "environment" {
  type = string
}

variable "repos" {
  type    = list(string)
  default = null # Default to null in case the repository isn't provided in platform-config.yml
}
