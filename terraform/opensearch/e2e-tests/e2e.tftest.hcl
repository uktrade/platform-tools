variables {
  vpc_name    = "sandbox-opensearch"
  application = "opensearch-application"
  environment = "test"
  name        = "opensearch-name"
  config = {
    engine = "2.5"
    plan   = "tiny"
  }
}

run "setup_tests" {
  module {
    source = "./e2e-tests/setup"
  }
}

run "opensearch_e2e_test" {
  command = apply

  assert {
    condition     = aws_opensearch_domain.this.domain_name == "test-opensearch-name"
    error_message = "Should be: 'test-opensearch-name"
  }

  assert {
    condition     = aws_opensearch_domain.this.engine_version == "OpenSearch_2.5"
    error_message = "Should be: 'OpenSearch_2.5'"
  }

  assert {
    condition     = aws_opensearch_domain.this.cluster_config[0].dedicated_master_type == null
    error_message = "Should be: null"
  }

  assert {
    condition     = aws_opensearch_domain.this.cluster_config[0].dedicated_master_count == null
    error_message = "Should be: null"
  }

  assert {
    condition     = aws_opensearch_domain.this.cluster_config[0].dedicated_master_enabled == false
    error_message = "Should be: false"
  }

  assert {
    condition     = aws_opensearch_domain.this.cluster_config[0].enable_ha == false
    error_message = "Should be: false"
  }

  assert {
    condition     = aws_opensearch_domain.this.cluster_config[0].instance_type == "t3.small.search"
    error_message = "Should be: 't3.small.search'"
  }

  assert {
    condition     = aws_opensearch_domain.this.cluster_config[0].instance_count == 1
    error_message = "Should be: 1"
  }

  assert {
    condition     = aws_opensearch_domain.this.ebs_options[0].volume_size == 80
    error_message = "Should be: 80"
  }

  assert {
    condition     = aws_opensearch_domain.this.ebs_options[0].volume_type == "gp2"
    error_message = "Should be: 'gp2'"
  }

  assert {
    condition     = aws_opensearch_domain.this.ebs_options[0].throughput == 0
    error_message = "Should be: null"
  }

  assert {
    condition     = aws_opensearch_domain.this.auto_tune_options[0].desired_state == "DISABLED"
    error_message = "Should be: 'DISABLED'"
  }

  assert {
    condition     = aws_ssm_parameter.opensearch_endpoint.name == "/copilot/opensearch-application/test/secrets/OPENSEARCH_NAME_ENDPOINT"
    error_message = "Should be: '/copilot/opensearch-application/test/secrets/OPENSEARCH_NAME_ENDPOINT'"
  }

  assert {
    condition     = aws_ssm_parameter.opensearch_endpoint.description == "opensearch_password"
    error_message = "Should be: 'opensearch_password'"
  }
}
