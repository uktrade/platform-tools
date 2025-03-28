
variable "sources" {
  type = list(object({
    source_bucket_arn  = string
    source_kms_key_arn = optional(string)
    worker_role_arn    = string
  }))
}

variable "destination_bucket_arn" {
  type    = string
  default = ""
}

variable "destination_bucket_identifier" {
  type    = string
  default = ""
}

variable "destination_kms_key_arn" {
  type    = string
  default = ""
}
