variable "aws_account_name" {
  default = null
  type    = string
}

variable "custom_key_policy" {
  default     = null
  type        = string
  description = "Used to override the default key policy on the KMS key that encrypts the state file in cases it is required."
}