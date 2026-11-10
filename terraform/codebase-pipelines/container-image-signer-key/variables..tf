variable "application" {
  type = string
}

variable "deploy_account_ids" {
  type     = list(string)
  default  = null
  nullable = true
}

variable "env_config" {
  type = any
  default = {}
}

variable "key_alias_mappings" {
  type     = any
  default  = null
  nullable = true
}

variable "tags" {
  type     = any
  default  = null
  nullable = true
}
