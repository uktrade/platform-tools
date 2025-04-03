variable "application" {
  type = string
}

variable "environment" {
  type = string
}

variable "config" {
  type = object({
    domain_prefix           = optional(string)
    env_root                = optional(string)
    cdn_domains_list        = optional(map(list(string)))
    additional_address_list = optional(list(string))
    enable_logging          = optional(bool)
    cache_policy            = optional(map(any))
    origin_request_policy   = optional(map(any))
    paths                   = optional(any)

    # CDN default overrides
    viewer_certificate_minimum_protocol_version = optional(string)
    viewer_certificate_ssl_support_method       = optional(string)
    forwarded_values_query_string               = optional(bool)
    forwarded_values_headers                    = optional(list(string))
    forwarded_values_forward                    = optional(string)
    viewer_protocol_policy                      = optional(string)
    allowed_methods                             = optional(list(string))
    cached_methods                              = optional(list(string))
    default_waf                                 = optional(string)
    cdn_timeout_seconds                         = optional(number)
    origin_protocol_policy                      = optional(string)
    origin_ssl_protocols                        = optional(list(string))
    cdn_compress                                = optional(bool)
    cdn_geo_restriction_type                    = optional(string)
    cdn_geo_locations                           = optional(list(string))
    cdn_logging_bucket                          = optional(string)
    cdn_logging_bucket_prefix                   = optional(string)
  })

  validation {
    condition = var.config.cdn_domains_list == null ? true : alltrue([
      for k, v in var.config.cdn_domains_list : ((length(k) <= 63) && (length(k) >= 3))
    ])
    error_message = "Items in cdn_domains_list should be between 3 and 63 characters long."
  }

}

# Pulled in from output in ALB module
variable "origin_verify_secret_id" {
  description = "The ID of the secret used for origin verification"
  type        = string
}
