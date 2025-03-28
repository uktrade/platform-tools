variables {
  vpc_name    = "sandbox-elasticache-redis"
  application = "test-application"
  environment = "test-environment"
  name        = "test-redis"
  config = {
    "engine" = "6.2",
    "plan"   = "small",
  }
}

run "setup_tests" {
  module {
    source = "./e2e-tests/setup"
  }
}

run "e2e_test" {
  # e2e test takes ~ 20 [mins] to run #

  command = apply

  ### Test aws_elasticache_replication_group resource ###
  assert {
    condition     = aws_elasticache_replication_group.redis.replication_group_id == "test-redis-test-environment"
    error_message = "Invalid config for aws_elasticache_replication_group replication_group_id"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.subnet_group_name == "test-redis-test-environment-cache-subnet"
    error_message = "Invalid config for aws_elasticache_replication_group subnet_group_name"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.engine == "redis"
    error_message = "Invalid config for aws_elasticache_replication_group engine"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.engine_version == "6.2"
    error_message = "Invalid config for aws_elasticache_replication_group engine_version"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.num_node_groups == 1
    error_message = "Invalid config for aws_elasticache_replication_group num_node_groups"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.replicas_per_node_group == 1
    error_message = "Invalid config for aws_elasticache_replication_group replicas_per_node_group"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.transit_encryption_enabled == true
    error_message = "Invalid config for aws_elasticache_replication_group transit_encryption_enabled"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.at_rest_encryption_enabled == "true"
    error_message = "Invalid config for aws_elasticache_replication_group at_rest_encryption_enabled"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.apply_immediately == false
    error_message = "Invalid config for aws_elasticache_replication_group apply_immediately"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.automatic_failover_enabled == false
    error_message = "Invalid config for aws_elasticache_replication_group automatic_failover_enabled"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.multi_az_enabled == false
    error_message = "Invalid config for aws_elasticache_replication_group multi_az_enabled"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.auth_token_update_strategy == "ROTATE"
    error_message = "Invalid config for aws_elasticache_replication_group auth_token_update_strategy"
  }

  assert {
    condition     = [for el in aws_elasticache_replication_group.redis.log_delivery_configuration : el.destination if el.log_type == "engine-log"][0] == "/aws/elasticache/test-redis/test-environment/test-redisRedis/engine"
    error_message = "Invalid config for aws_elasticache_replication_group log_delivery_configuration"
  }

  assert {
    condition     = [for el in aws_elasticache_replication_group.redis.log_delivery_configuration : el.destination if el.log_type == "slow-log"][0] == "/aws/elasticache/test-redis/test-environment/test-redisRedis/slow"
    error_message = "Invalid config for aws_elasticache_replication_group log_delivery_configuration"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.engine_version_actual == "6.2.6"
    error_message = "Invalid config for aws_elasticache_replication_group engine_version_actual"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.network_type == "ipv4"
    error_message = "Invalid config for aws_elasticache_replication_group network_type"
  }

  assert {
    condition     = aws_elasticache_replication_group.redis.auto_minor_version_upgrade == "true"
    error_message = "Invalid config for aws_elasticache_replication_group auto_minor_version_upgrade"
  }

  assert {
    condition     = aws_ssm_parameter.endpoint.value == "rediss://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379"
    error_message = "Invalid config for value attribute in aws_ssm_parameter endpoint resource"
  }

  assert {
    condition     = aws_ssm_parameter.endpoint_short.value == "rediss://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379"
    error_message = "Invalid config for value attribute in aws_ssm_parameter endpoint_short resource"
  }

  assert {
    condition     = aws_ssm_parameter.redis_url.value == "rediss://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379?ssl_cert_reqs=CERT_REQUIRED"
    error_message = "Invalid config for value attribute in aws_ssm_parameter redis_url resource"
  }

  assert {
    condition     = aws_ssm_parameter.endpoint.key_id == aws_kms_key.ssm_redis_endpoint.arn
    error_message = "Should be: arn for aws_kms_key.ssm_redis_endpoint resource"
  }

  assert {
    condition     = aws_ssm_parameter.endpoint_short.key_id == aws_kms_key.ssm_redis_endpoint.arn
    error_message = "Should be: arn for aws_kms_key.ssm_redis_endpoint resource"
  }

  assert {
    condition     = aws_ssm_parameter.redis_url.key_id == aws_kms_key.ssm_redis_endpoint.arn
    error_message = "Should be: arn for aws_kms_key.ssm_redis_endpoint resource"
  }
}
