variable "application" {
  type = string
}

variable "deploy_account_ids" {
  type = list(string)
}

variable "static_signer_alias" {
  type = string
}

variable "key_alias_mappings" {
  type = any #map(object)
}

variable "tags" {
  type = any #map(object)
}


