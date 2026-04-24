variable "name" {
  type = string
}


variable "schedule" {
  type = any
}

variable "retries" {
  type    = number
  default = null
}

variable "timeout" {
  type    = number
  default = null
}

variable "vpc_id" {
  type = string
}

variable "task_definition_arn" {
  type = string
}


variable "cluster_id" {
  type = any
}

variable "subnet_ids" {
  type = any
}

variable "tags" {
  type = any
}
