variable "aws_account_name" {
  default = null
  type    = string
}

variable "custom_key_policy" {
  default     = null
  type        = string
  description = "Used to override the default key policy on the KMS key that encrypts the state file in cases it is required."
}

variable "key_policy_role_name_suffix" {
  default     = null
  type        = string
  description = "Used to override the aws_account_name variable where it does not match the OIDC role name suffix."
}