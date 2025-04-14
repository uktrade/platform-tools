mock_provider "aws" {
  alias = "domain-cdn"
}

mock_provider "aws" {
  alias = "domain"
}

mock_provider "aws" {

}

override_data {
  target = data.aws_route53_zone.domain-root
  values = {
    count = 0
    name  = "my-application.uktrade.digital"
  }
}

override_data {
  target = data.aws_secretsmanager_secret_version.origin_verify_secret_version
  values = {
    secret_string = "{\"HEADERVALUE\": \"some-secret\"}"
  }
}

variables {
  application = "app"
  environment = "env"
  vpc_name    = "vpc-name"
  config = {
    domain_prefix    = "dom-prefix",
    cdn_domains_list = { "dev.my-application.uktrade.digital" : ["internal", "my-application.uktrade.digital"], "dev2.my-application.uktrade.digital" : ["internal", "my-application.uktrade.digital", "disable_cdn"] }
  }
  origin_verify_secret_id = "dummy123"
}


run "aws_route53_record_unit_test" {
  command = plan

  assert {
    condition     = aws_route53_record.cdn-address["dev.my-application.uktrade.digital"].name == "dev.my-application.uktrade.digital"
    error_message = "Should be: dev.my-application.uktrade.digital"
  }

}

run "aws_acm_certificate_unit_test" {
  command = plan

  assert {
    condition     = aws_acm_certificate.certificate["dev.my-application.uktrade.digital"].domain_name == "dev.my-application.uktrade.digital"
    error_message = "Should be: dev.my-application.uktrade.digital"
  }

}

run "aws_cloudfront_distribution_unit_test" {
  command = plan

  assert {
    condition     = [for k in aws_cloudfront_distribution.standard["dev.my-application.uktrade.digital"].aliases : true if k == "dev.my-application.uktrade.digital"][0] == true
    error_message = "Should be: [ dev.my-application.uktrade.digital, ]"
  }

}

run "aws_route53_record_unit_test_prod" {
  command = plan

  variables {
    application = "app"
    environment = "prod"
    config = {
      domain_prefix    = "dom-prefix",
      cdn_domains_list = { "dev.my-application.uktrade.digital" : ["internal", "my-application.uktrade.digital"], "dev2.my-application.uktrade.digital" : ["internal", "my-application.uktrade.digital", "enable_record"] }
    }
  }

  assert {
    condition     = aws_route53_record.cdn-address["dev2.my-application.uktrade.digital"].name == "dev2.my-application.uktrade.digital"
    error_message = "Should be: dev2.my-application.uktrade.digital"
  }

}

run "domain_length_validation_tests" {
  command = plan

  variables {
    application = "app"
    environment = "env"
    config = {
      domain_prefix    = "dom-prefix",
      cdn_domains_list = { "a-very-long-domain-name-used-to-test-length-validation.my-application.uktrade.digital" : ["internal", "my-application.uktrade.digital"] }
    }
  }

  expect_failures = [
    var.config.cdn_domains_list
  ]
}

run "domain_length_validation_tests_succeed_with_empty_config" {
  command = plan

  variables {
    application = "app"
    environment = "env"
    config      = {}
  }

  assert {
    condition     = var.config.cdn_domains_list == null
    error_message = "Should be: null"
  }
}

run "cdn_read_timeout_is_set_to_30_seconds_by_default" {
  command = plan

  assert {
    condition = [
      for k in aws_cloudfront_distribution.standard["dev.my-application.uktrade.digital"].origin :
      k.custom_origin_config[0].origin_read_timeout
      if k.domain_name == "internal.env.app.uktrade.digital"
    ][0] == 30
    error_message = "Should be: 30 seconds"
  }
}

run "cdn_read_timeout_is_set_to_config_specified_value_when_provided" {
  command = plan

  variables {
    config = {
      cdn_domains_list    = { "dev.my-application.uktrade.digital" : ["internal", "my-application.uktrade.digital"] }
      cdn_timeout_seconds = 60
    }
  }
  assert {
    condition = [
      for k in aws_cloudfront_distribution.standard["dev.my-application.uktrade.digital"].origin :
      k.custom_origin_config[0].origin_read_timeout
      if k.domain_name == "internal.env.app.uktrade.digital"
    ][0] == 60
    error_message = "Should be: 60 seconds"
  }
}

# test minimum cache policy
run "validate_cache_policy" {
  command = plan

  variables {
    config = {
      cache_policy = {
        "test" = {
          min_ttl               = 1
          max_ttl               = 3600
          default_ttl           = 1
          cookies_config        = "all"
          header                = "none"
          query_string_behavior = "none"
        }
      }
    }
  }

  assert {
    condition     = aws_cloudfront_cache_policy.cache_policy["test"].min_ttl == 1
    error_message = "Cache policy min_ttl does not match expected value."
  }
  assert {
    condition     = aws_cloudfront_cache_policy.cache_policy["test"].max_ttl == 3600
    error_message = "Cache policy max_ttl does not match expected value."
  }
  assert {
    condition     = aws_cloudfront_cache_policy.cache_policy["test"].default_ttl == 1
    error_message = "Cache policy default_ttl does not match expected value."
  }
  assert {
    condition     = aws_cloudfront_cache_policy.cache_policy["test"].parameters_in_cache_key_and_forwarded_to_origin[0].cookies_config[0].cookie_behavior == "all" #var.config.cache_policy.cookies_config
    error_message = "Cache policy cookie_behavior does not match expected value."
  }
  assert {
    condition     = aws_cloudfront_cache_policy.cache_policy["test"].parameters_in_cache_key_and_forwarded_to_origin[0].headers_config[0].header_behavior == "none" #var.config.cache_policy.header
    error_message = "Cache policy header_behavior does not match expected value."
  }
  assert {
    condition     = aws_cloudfront_cache_policy.cache_policy["test"].parameters_in_cache_key_and_forwarded_to_origin[0].query_strings_config[0].query_string_behavior == "none" #var.config.cache_policy.query_string_behavior
    error_message = "Cache policy query_string_behavior does not match expected value."
  }

}

# Test for cookie list
run "validate_cache_policy_cookie_list" {
  command = plan

  variables {
    config = {
      cache_policy = {
        "test" = {
          min_ttl        = 1
          max_ttl        = 3600
          default_ttl    = 1
          cookies_config = "whitelist"
          cookie_list : ["my-cookie"]
          header                = "none"
          query_string_behavior = "all"
        }
      }
    }
  }
  assert {
    condition     = aws_cloudfront_cache_policy.cache_policy["test"].parameters_in_cache_key_and_forwarded_to_origin[0].cookies_config[0].cookie_behavior == "whitelist"
    error_message = "Cache policy cookie_behavior does not match expected value."
  }
  assert {
    condition     = contains(aws_cloudfront_cache_policy.cache_policy["test"].parameters_in_cache_key_and_forwarded_to_origin[0].cookies_config[0].cookies[0].items, "my-cookie")
    error_message = "Cache policy cookies does not match expected value."
  }
}

# Test for header list
run "validate_cache_policy_header_list" {
  command = plan

  variables {
    config = {
      cache_policy = {
        "test" = {
          min_ttl               = 1
          max_ttl               = 3600
          default_ttl           = 1
          cookies_config        = "all"
          header                = "whitelist"
          headers_list          = ["my-header"]
          query_string_behavior = "all"
        }
      }
    }
  }
  assert {
    condition     = aws_cloudfront_cache_policy.cache_policy["test"].parameters_in_cache_key_and_forwarded_to_origin[0].headers_config[0].header_behavior == "whitelist"
    error_message = "Cache policy header_behavior does not match expected value."
  }
  assert {
    condition     = contains(aws_cloudfront_cache_policy.cache_policy["test"].parameters_in_cache_key_and_forwarded_to_origin[0].headers_config[0].headers[0].items, "my-header")
    error_message = "Cache policy headers does not match expected value."
  }
}


# Test for query list
run "validate_cache_policy_query_strings" {
  command = plan

  variables {
    config = {
      cache_policy = {
        "test" = {
          min_ttl               = 1
          max_ttl               = 3600
          default_ttl           = 1
          cookies_config        = "all"
          header                = "none"
          query_string_behavior = "whitelist"
          cache_policy_query_strings : ["q", "test"]
        }
      }
    }
  }
  assert {
    condition     = aws_cloudfront_cache_policy.cache_policy["test"].parameters_in_cache_key_and_forwarded_to_origin[0].query_strings_config[0].query_string_behavior == "whitelist"
    error_message = "Cache policy query_string_behavior does not match expected value."
  }
  assert {
    condition     = contains(aws_cloudfront_cache_policy.cache_policy["test"].parameters_in_cache_key_and_forwarded_to_origin[0].query_strings_config[0].query_strings[0].items, "test")
    error_message = "Cache policy query_strings does not match expected value."
  }
}

# Test multiple cache policy
run "validate_multiple_cache_policys" {
  command = plan

  variables {
    config = {
      cache_policy = {
        "test" = {
          min_ttl               = 1
          max_ttl               = 3600
          default_ttl           = 1
          cookies_config        = "all"
          header                = "none"
          query_string_behavior = "none"
        }
        "test2" = {
          min_ttl               = 2
          max_ttl               = 3600
          default_ttl           = 1
          cookies_config        = "all"
          header                = "none"
          query_string_behavior = "none"
        }
      }
    }
  }
  assert {
    condition     = aws_cloudfront_cache_policy.cache_policy["test"].min_ttl == 1
    error_message = "Cache policy min_ttl does not match expected value."
  }
  assert {
    condition     = aws_cloudfront_cache_policy.cache_policy["test2"].min_ttl == 2
    error_message = "Cache policy min_ttl does not match expected value."
  }

}

# No config should be set, just policy name
run "validate_origin_request_policy" {
  command = plan

  variables {
    config = {
      origin_request_policy = {
        "test" = {}
      }
    }
  }
  assert {
    condition     = aws_cloudfront_origin_request_policy.origin_request_policy["test"].cookies_config[0].cookie_behavior == "all"
    error_message = "Cache policy cookie_behavior does not match expected value."
  }
  assert {
    condition     = aws_cloudfront_origin_request_policy.origin_request_policy["test"].headers_config[0].header_behavior == "allViewer"
    error_message = "Cache policy header_behavior does not match expected value."
  }
  assert {
    condition     = aws_cloudfront_origin_request_policy.origin_request_policy["test"].query_strings_config[0].query_string_behavior == "all"
    error_message = "Cache policy query_string_behavior does not match expected value."
  }
}

# Test with no cache policy assigned defaults should be set.
run "validate_default_cache_policy_not_set" {
  command = plan

  variables {
    config = {
      # cache_policy = {"test-policy" = {}}
      # origin_request_policy = {"test-origin-request" = {}}
      domain_prefix    = "dom-prefix",
      cdn_domains_list = { "dev.my-application.uktrade.digital" : ["internal", "my-application.uktrade.digital"] }
    }
  }
  assert {
    condition     = contains(aws_cloudfront_distribution.standard["dev.my-application.uktrade.digital"].default_cache_behavior[0].forwarded_values[0].headers, "*")
    error_message = "header does not match expected value."
  }
  assert {
    condition     = aws_cloudfront_distribution.standard["dev.my-application.uktrade.digital"].default_cache_behavior[0].forwarded_values[0].query_string == true
    error_message = "query string does not match expected value."
  }
  assert {
    condition     = aws_cloudfront_distribution.standard["dev.my-application.uktrade.digital"].default_cache_behavior[0].forwarded_values[0].cookies[0].forward == "all"
    error_message = "forward value does not match expected value."
  }
}

# Test with cache policy assigned and default cache behaviour.
run "validate_default_cache_policy_set" {
  command = plan

  variables {
    application = "app"
    environment = "env"
    config = {
      cache_policy = {
        "test-policy" = {
          min_ttl               = 1
          max_ttl               = 3600
          default_ttl           = 1
          cookies_config        = "all"
          header                = "none"
          query_string_behavior = "none"
        }
      }
      origin_request_policy = { "test-origin-request" = {} }
      domain_prefix         = "dom-prefix",
      cdn_domains_list      = { "dev.my-application.uktrade.digital" : ["internal", "my-application.uktrade.digital"] }
      paths = {
        "dev.my-application.uktrade.digital" = {
          default = {
            cache   = "test-policy"
            request = "test-origin-request"
          }
        }
      }
    }
  }
  assert {
    condition     = length(aws_cloudfront_distribution.standard["dev.my-application.uktrade.digital"].default_cache_behavior[0].forwarded_values) == 0
    error_message = "default forwarded values should not be set."
  }
}

# Test with cache policy assigned and default cache behaviour multiple domains.
run "validate_default_cache_policy_set_multiple_domains" {
  command = plan

  variables {
    application = "app"
    environment = "env"
    config = {
      cache_policy = {
        "test-policy" = {
          min_ttl               = 1
          max_ttl               = 3600
          default_ttl           = 1
          cookies_config        = "all"
          header                = "none"
          query_string_behavior = "none"
        }
      }
      origin_request_policy = { "test-origin-request" = {} }
      domain_prefix         = "dom-prefix",
      cdn_domains_list      = { "dev.my-application.uktrade.digital" : ["internal", "my-application.uktrade.digital"], "dev2.my-application.uktrade.digital" : ["internal-2", "my-application.uktrade.digital"] }
      paths = {
        "dev.my-application.uktrade.digital" = {
          default = {
            cache   = "test-policy"
            request = "test-origin-request"
          }
        },
        "dev2.my-application.uktrade.digital" = {
          default = {
            cache   = "test-policy"
            request = "test-origin-request"
          }
        }
      }
    }
  }
  assert {
    condition     = length(aws_cloudfront_distribution.standard["dev2.my-application.uktrade.digital"].default_cache_behavior[0].forwarded_values) == 0
    error_message = "default forwarded values should not be set."
  }
}

# Test with cache policy assigned and ordered cache behaviour.
run "validate_ordered_cache_policy_set" {
  command = plan

  variables {
    application = "app"
    environment = "env"
    config = {
      cache_policy = {
        "test-policy" = {
          min_ttl               = 1
          max_ttl               = 3600
          default_ttl           = 1
          cookies_config        = "all"
          header                = "none"
          query_string_behavior = "none"
        }
      }
      origin_request_policy = { "test-origin-request" = {} }
      domain_prefix         = "dom-prefix",
      cdn_domains_list      = { "dev.my-application.uktrade.digital" : ["internal", "my-application.uktrade.digital"] }
      paths = {
        "dev.my-application.uktrade.digital" = {
          additional = [
            {
              path    = "/static"
              cache   = "test-policy"
              request = "test-origin-request"
            },
            {
              path    = "/images"
              cache   = "test-policy"
              request = "test-origin-request"
            }
          ]
        }
      }
    }
  }

  assert {
    condition     = aws_cloudfront_distribution.standard["dev.my-application.uktrade.digital"].ordered_cache_behavior[0].path_pattern == "/static"
    error_message = "default forwarded values should not be set."
  }
  assert {
    condition     = aws_cloudfront_distribution.standard["dev.my-application.uktrade.digital"].ordered_cache_behavior[1].path_pattern == "/images"
    error_message = "default forwarded values should not be set."
  }
}
