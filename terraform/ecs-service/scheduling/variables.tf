variable "name" {
  type = string
}

variable "schedule" {
  type = string
}

variable "retries" {
  type = number
}

variable "timeout_seconds" {
  type = number
}

variable "vpc_id" {
  type = string
}

variable "task_definition_arn" {
  type = string
}


variable "cluster_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "tags" {
  type = map(any)
}

variable "log_group_arn" {
  type = string
}
