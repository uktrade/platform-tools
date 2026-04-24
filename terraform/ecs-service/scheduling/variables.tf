variable "name" {
  type = string
}

variable "schedule" {
  type = string
}

variable "retries" {
  type    = number
  default = null
}

variable "timeout_seconds" {
  type    = number
  default = 86400 # set timeout to 24 hours to avoid runaway state machines caused by the default provided by AWS (99999999, which is approximately 3 years). See here: https://docs.aws.amazon.com/step-functions/latest/dg/state-task.html
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
