data "aws_wafv2_web_acl" "waf-default" {
  provider = aws.domain-cdn
  name     = local.cdn_defaults.default_waf
  scope    = "CLOUDFRONT"
}

resource "aws_acm_certificate" "certificate" {
  provider = aws.domain-cdn
  for_each = local.cdn_domains_list

  domain_name       = each.key
  validation_method = "DNS"
  key_algorithm     = "RSA_2048"
  tags              = local.tags
  lifecycle {
    create_before_destroy = true
    prevent_destroy       = true
  }
}

resource "aws_acm_certificate_validation" "cert-validate" {
  provider                = aws.domain-cdn
  for_each                = local.cdn_domains_list
  certificate_arn         = aws_acm_certificate.certificate[each.key].arn
  validation_record_fqdns = [for record in aws_route53_record.validation-record : record.fqdn]
  lifecycle {
    prevent_destroy = true
  }
}

data "aws_route53_zone" "domain-root" {
  provider = aws.domain-cdn
  for_each = local.cdn_domains_list
  name     = each.value[1]
}

resource "aws_route53_record" "validation-record" {
  provider = aws.domain-cdn
  for_each = local.cdn_domains_list
  zone_id  = data.aws_route53_zone.domain-root[each.key].zone_id
  name     = tolist(aws_acm_certificate.certificate[each.key].domain_validation_options)[0].resource_record_name
  type     = tolist(aws_acm_certificate.certificate[each.key].domain_validation_options)[0].resource_record_type
  records  = [tolist(aws_acm_certificate.certificate[each.key].domain_validation_options)[0].resource_record_value]
  ttl      = 300
  lifecycle {
    prevent_destroy = true
  }
}

# These data exports are only run if there is a cache policy configured in platform-config.yml
data "aws_cloudfront_cache_policy" "policy-name" {
  provider = aws.domain-cdn
  for_each = coalesce(var.config.cache_policy, {})

  name       = "${each.key}-${var.application}-${var.environment}"
  depends_on = [aws_cloudfront_cache_policy.cache_policy]
}

data "aws_cloudfront_origin_request_policy" "request-policy-name" {
  provider = aws.domain-cdn
  for_each = coalesce(var.config.origin_request_policy, {})

  name       = "${each.key}-${var.application}-${var.environment}"
  depends_on = [aws_cloudfront_origin_request_policy.origin_request_policy]
}

data "aws_secretsmanager_secret_version" "origin_verify_secret_version" {
  for_each  = toset(length(local.cdn_domains_list) > 0 ? [""] : [])
  secret_id = var.origin_verify_secret_id
}

resource "aws_cloudfront_distribution" "standard" {
  # checkov:skip=CKV_AWS_305:This is managed in the application.
  # checkov:skip=CKV_AWS_310:No fail-over origin required.
  # checkov:skip=CKV2_AWS_32:Response headers policy not required.
  # checkov:skip=CKV2_AWS_47:WAFv2 WebACL rules are set in https://gitlab.ci.uktrade.digital/webops/terraform-waf
  # checkov:skip=CKV_AWS_174:We are already setting TLS v1.2 as minimum but it's not picking it up correctly
  depends_on = [
    aws_acm_certificate_validation.cert-validate,
    aws_cloudfront_cache_policy.cache_policy,
    aws_cloudfront_origin_request_policy.origin_request_policy
  ]

  provider        = aws.domain-cdn
  for_each        = local.cdn_domains_list
  enabled         = true
  is_ipv6_enabled = true
  web_acl_id      = data.aws_wafv2_web_acl.waf-default.arn
  aliases         = [each.key]

  origin {
    domain_name = "${each.value[0]}.${local.domain_suffix}"
    origin_id   = "${each.value[0]}.${local.domain_suffix}"
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = local.cdn_defaults.origin.custom_origin_config.origin_protocol_policy
      origin_ssl_protocols   = local.cdn_defaults.origin.custom_origin_config.origin_ssl_protocols
      origin_read_timeout    = local.cdn_defaults.origin.custom_origin_config.cdn_timeout_seconds
    }
    custom_header {
      name  = "x-origin-verify"
      value = jsondecode(data.aws_secretsmanager_secret_version.origin_verify_secret_version[""].secret_string)["HEADERVALUE"]
    }
  }

  default_cache_behavior {
    allowed_methods        = local.cdn_defaults.allowed_methods
    cached_methods         = local.cdn_defaults.cached_methods
    target_origin_id       = "${each.value[0]}.${local.domain_suffix}"
    viewer_protocol_policy = local.cdn_defaults.viewer_protocol_policy
    compress               = local.cdn_defaults.compress

    # These 4 paramters (min_ttl, default_ttl, max_ttl and forwarded_values) are only used if there is no cache policy set on the default root path, 
    # therefore they need to be set to null if you want to use a cache policy on the root.
    # If the variable paths/{domain}/default is not set the default values are used. 
    min_ttl     = try(var.config.paths[each.key].default != null ? null : 0, 0)
    default_ttl = try(var.config.paths[each.key].default != null ? null : 86400, 86400)
    max_ttl     = try(var.config.paths[each.key].default != null ? null : 31536000, 31536000)

    dynamic "forwarded_values" {
      for_each = try(var.config.paths[each.key].default != null ? [] : ["default"], ["default"])
      content {
        query_string = local.cdn_defaults.forwarded_values.query_string
        headers      = local.cdn_defaults.forwarded_values.headers
        cookies {
          forward = local.cdn_defaults.forwarded_values.cookies.forward
        }
      }
    }

    # If the variable paths/{domain}/default/[cache/request] are set.
    cache_policy_id          = try(data.aws_cloudfront_cache_policy.policy-name[var.config.paths[each.key].default.cache].id, "")
    origin_request_policy_id = try(data.aws_cloudfront_origin_request_policy.request-policy-name[var.config.paths[each.key].default.request].id, "")
  }

  # If path based routing is set in platform-config.yml then this is run per path, you will always attach a policy to a path.
  dynamic "ordered_cache_behavior" {
    for_each = try(var.config.paths[each.key] != null ? [for k in var.config.paths[each.key].additional : k] : [], [])

    content {
      path_pattern             = ordered_cache_behavior.value.path
      target_origin_id         = "${each.value[0]}.${local.domain_suffix}"
      cache_policy_id          = data.aws_cloudfront_cache_policy.policy-name[ordered_cache_behavior.value.cache].id
      origin_request_policy_id = data.aws_cloudfront_origin_request_policy.request-policy-name[ordered_cache_behavior.value.request].id
      viewer_protocol_policy   = "redirect-to-https"
      allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
      cached_methods           = ["GET", "HEAD"]
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = false
    acm_certificate_arn            = aws_acm_certificate.certificate[each.key].arn
    minimum_protocol_version       = local.cdn_defaults.viewer_certificate.minimum_protocol_version
    ssl_support_method             = local.cdn_defaults.viewer_certificate.ssl_support_method
  }

  restrictions {
    geo_restriction {
      restriction_type = local.cdn_defaults.geo_restriction.restriction_type
      locations        = local.cdn_defaults.geo_restriction.locations
    }
  }

  dynamic "logging_config" {
    for_each = local.cdn_defaults.logging_config
    content {
      bucket          = local.cdn_defaults.logging_config.bucket
      include_cookies = false
      prefix          = each.key
    }
  }

  tags = local.tags
  lifecycle {
    prevent_destroy = true
  }
}

# This is only run if enable_cdn_record is set to true.
# Production default is false.
# Non prod this is true.
resource "aws_route53_record" "cdn-address" {
  provider = aws.domain-cdn

  for_each = local.cdn_records
  zone_id  = data.aws_route53_zone.domain-root[each.key].zone_id
  name     = each.key
  type     = "A"
  alias {
    name                   = aws_cloudfront_distribution.standard[each.key].domain_name
    zone_id                = aws_cloudfront_distribution.standard[each.key].hosted_zone_id
    evaluate_target_health = false
  }
  lifecycle {
    prevent_destroy = true
  }
}


# Create a CDN cache policy and origin request policy - Optional, but if one is set the the other needs to also be set.
# These resources are only needed if you need to apply caching on your CDN either on the root or path of your domain.
# There is a bug in the AWS provider where terraform is not able to in one terraform apply create the policy then attach the policy
# to the paths.  You need to create the resource first run terraform apply, then attach the resource to the path.
#
#|Error: Provider produced inconsistent final plan
#│
#│ When expanding the plan for module.extensions.module.cdn["<alb-name>"].aws_cloudfront_distribution.standard["<domain-name>"] to include new values learned so far
#│ during apply, provider "registry.terraform.io/hashicorp/aws" produced an invalid new value for .default_cache_behavior[0].origin_request_policy_id: was cty.StringVal(""), but now
#│ cty.StringVal("6b392d40-eb27-42d5-9e21-70f028b40bbf").
#│
#│ This is a bug in the provider, which should be reported in the provider's own issue tracker.
#
resource "aws_cloudfront_cache_policy" "cache_policy" {
  provider = aws.domain-cdn

  for_each = coalesce(var.config.cache_policy, {})

  name        = "${each.key}-${var.application}-${var.environment}"
  comment     = "Cache policy created for ${var.application}"
  default_ttl = each.value["default_ttl"]
  max_ttl     = each.value["max_ttl"]
  min_ttl     = each.value["min_ttl"]

  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = each.value["cookies_config"]

      # valid cookies config are none, all, whitelist, allExcept
      # cookie values can only be set if cookie_config is whitelist or allExcept.
      dynamic "cookies" {
        for_each = each.value["cookies_config"] == "whitelist" || each.value["cookies_config"] == "allExcept" ? [each.value["cookie_list"]] : []
        content {
          items = cookies.value
        }
      }
    }
    headers_config {
      header_behavior = each.value["header"]

      # valid headers config are none, all, whitelist, allExcept
      # header values can only be set if header is whitelist.
      dynamic "headers" {
        for_each = each.value["header"] == "whitelist" ? [each.value["headers_list"]] : []
        content {
          items = headers.value
        }
      }
    }
    # valiid query string behaviours are none, all, whitelist, allExcept
    # query string values can only be set if behaviour is whitelist or allExcept.
    query_strings_config {
      query_string_behavior = each.value["query_string_behavior"]

      dynamic "query_strings" {
        for_each = each.value["query_string_behavior"] == "whitelist" || each.value["query_string_behavior"] == "allExcept" ? [each.value["cache_policy_query_strings"]] : []
        content {
          items = query_strings.value
        }
      }
    }
    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true
  }
  lifecycle {
    prevent_destroy = true
  }
}

# We do not cache origin requests, so leaving all config as default.
resource "aws_cloudfront_origin_request_policy" "origin_request_policy" {
  provider = aws.domain-cdn

  for_each = coalesce(var.config.origin_request_policy, {})

  name    = "${each.key}-${var.application}-${var.environment}"
  comment = "Origin request policy created for ${var.application}"
  cookies_config {
    cookie_behavior = "all"
  }
  headers_config {
    header_behavior = "allViewer"
  }
  query_strings_config {
    query_string_behavior = "all"
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_cloudfront_monitoring_subscription" "additional_metrics" {
  provider = aws.domain-cdn

  for_each        = aws_cloudfront_distribution.standard
  distribution_id = aws_cloudfront_distribution.standard[each.key].id

  monitoring_subscription {
    realtime_metrics_subscription_config {
      realtime_metrics_subscription_status = "Enabled"
    }
  }
}
