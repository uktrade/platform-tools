locals {
  tags = {
    application         = var.application
    environment         = var.environment
    managed-by          = "DBT Platform - Terraform"
    copilot-application = var.application
    copilot-environment = var.environment
  }

  # The primary domain for every application follows the naming standard documented under https://github.com/uktrade/terraform-platform-modules/blob/main/README.md#application-load-balancer-module
  env_domain_suffix = var.dns_account_name == "live" ? "prod.uktrade.digital" : "uktrade.digital"
  domain_suffix = var.environment == "prod" ? coalesce(var.config.env_root, "${var.application}.${local.env_domain_suffix}") : coalesce(var.config.env_root, "${var.environment}.${var.application}.${local.env_domain_suffix}")

  # Cull the domain from the cdn_domains_list if "disable_cdn" is set in the value list.
  cdn_domains_list = try({ for k, v in var.config.cdn_domains_list : k => v if !contains(v, "disable_cdn") }, {})

  # To avoid overwrites in prod we do not want to update R53 records by default, can be bypassed if "enable_record" is set in the value list.
  cdn_records = { for k, v in local.cdn_domains_list : k => v if(var.environment != "prod" || contains(v, "enable_record")) }

  # CDN logging buckets
  logging_bucket = var.environment == "prod" ? "dbt-cloudfront-logs-prod.s3-eu-west-2.amazonaws.com" : "dbt-cloudfront-logs.s3-eu-west-2.amazonaws.com"

  # Default configuration for CDN.
  cdn_defaults = {
    viewer_protocol_policy = coalesce(var.config.viewer_protocol_policy, "redirect-to-https")
    viewer_certificate = {
      minimum_protocol_version = coalesce(var.config.viewer_certificate_minimum_protocol_version, "TLSv1.2_2021")
      ssl_support_method       = coalesce(var.config.viewer_certificate_ssl_support_method, "sni-only")
    }
    forwarded_values = {
      query_string = coalesce(var.config.forwarded_values_query_string, true)
      headers      = coalesce(var.config.forwarded_values_headers, ["*"])
      cookies = {
        forward = coalesce(var.config.forwarded_values_forward, "all")
      }
    }
    allowed_methods = coalesce(var.config.allowed_methods, ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"])
    cached_methods  = coalesce(var.config.cached_methods, ["GET", "HEAD"])

    origin = {
      custom_origin_config = {
        origin_protocol_policy = coalesce(var.config.origin_protocol_policy, "https-only")
        origin_ssl_protocols   = coalesce(var.config.origin_ssl_protocols, ["TLSv1.2"])
        cdn_timeout_seconds    = coalesce(var.config.cdn_timeout_seconds, 30)
      }
    }
    compress = coalesce(var.config.cdn_compress, true)

    geo_restriction = {
      restriction_type = coalesce(var.config.cdn_geo_restriction_type, "none")
      locations        = coalesce(var.config.cdn_geo_locations, [])
    }

    # By default logging is off on all distros.
    logging_config = coalesce(var.config.enable_logging, false) ? { bucket = local.logging_bucket } : {}

    default_waf = var.environment == "prod" ? coalesce(var.config.default_waf, "waf_sentinel_684092750218_default") : coalesce(var.config.default_waf, "waf_sentinel_011755346992_default")
  }
}
