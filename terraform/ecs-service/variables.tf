variable "application" {
  type = string
}

variable "environment" {
  type = string
}

variable "service_config" {
  type = object({
    name = string
    type = string

    http = object({
      path             = string
      target_container = string
      healthcheck = optional(object({
        path                = optional(string)
        port                = optional(number)
        success_codes       = optional(string)
        healthy_threshold   = optional(number)
        unhealthy_threshold = optional(number)
        interval            = optional(string)
        timeout             = optional(string)
        grace_period        = optional(string)
      }))
    })

    sidecars = optional(map(object({
      port      = optional(number)
      image     = optional(string)
      variables = optional(map(string))
      secrets   = optional(map(string))
    })))

    image = object({
      port     = optional(number)
      location = string
    })

    cpu        = number
    memory     = number
    count      = number
    exec       = optional(bool)
    entrypoint = optional(string)

    network = optional(object({
      connect = optional(bool)
      vpc = optional(object({
        placement = optional(string)
      }))
    }))

    storage = optional(object({
      readonly_fs = bool
    }))

    variables = optional(map(any))
    secrets   = optional(map(string))

    environments = optional(map(object({
      http = optional(object({
        alb   = optional(string)
        alias = optional(string)
      }))
      sidecars = optional(map(object({
        variables = optional(map(any))
      })))
      variables = optional(map(any))
      secrets   = optional(map(string))
      image = optional(object({
        port     = optional(number)
        location = optional(string)
      }))
      cpu        = optional(number)
      memory     = optional(number)
      count      = optional(number)
      exec       = optional(bool)
      entrypoint = optional(string)
      network = optional(object({
        connect = optional(bool)
        vpc = optional(object({
          placement = optional(string)
        }))
      }))

      storage = optional(object({
        readonly_fs = optional(string)
      }))
    })))
  })
}

variable "vpc_name" {
  type    = string
  default = "platform-sandbox-dev" #TODO - Remove hardcoding
}
