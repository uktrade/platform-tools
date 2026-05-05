mock_provider "aws" {}

variables {
  platform_version = "10.2.0"
  application      = "demodjango"
}

run "test_environment_ssm_parameter" {
  command = plan

  variables {
    environment   = "dev"
    service_name  = null
    pipeline_type = null
  }

  assert {
    condition     = aws_ssm_parameter.platform_version.name == "/platform/version/applications/demodjango/environments/dev"
    error_message = "SSM parameter name should be '/platform/version/applications/demodjango/environments/dev'"
  }

  assert {
    condition = aws_ssm_parameter.platform_version.tags == tomap({
      "application" : "demodjango",
      "environment" : "dev",
      "managed-by" : "DBT Platform - Environment Terraform",
    })
    error_message = "SSM parameter tags do not match expected values"
  }
}

run "test_service_ssm_parameter" {
  command = plan

  variables {
    environment   = "dev"
    service_name  = "web"
    pipeline_type = null
  }

  assert {
    condition     = aws_ssm_parameter.platform_version.name == "/platform/version/applications/demodjango/environments/dev/services/web"
    error_message = "SSM parameter name should be '/platform/version/applications/demodjango/environments/dev/services/web'"
  }

  assert {
    condition = aws_ssm_parameter.platform_version.tags == tomap({
      "application" : "demodjango",
      "environment" : "dev",
      "service" : "web",
      "managed-by" : "DBT Platform - Service Terraform",
    })
    error_message = "SSM parameter tags do not match expected values"
  }
}

run "test_codebase_pipeline_ssm_parameter" {
  command = plan

  variables {
    environment   = null
    service_name  = null
    pipeline_type = "codebase-pipeline"
  }

  assert {
    condition     = aws_ssm_parameter.platform_version.name == "/platform/version/applications/demodjango/codebase-pipelines"
    error_message = "SSM parameter name should be '/platform/version/applications/demodjango/codebase-pipelines'"
  }

  assert {
    condition = aws_ssm_parameter.platform_version.tags == tomap({
      "application" : "demodjango",
      "pipeline" : "codebase-pipelines",
      "managed-by" : "DBT Platform - Codebase Pipelines Terraform",
    })
    error_message = "SSM parameter tags do not match expected values"
  }
}

run "test_environment_pipeline_ssm_parameter" {
  command = plan

  variables {
    environment   = null
    service_name  = null
    pipeline_type = "environment-pipeline"
  }

  assert {
    condition     = aws_ssm_parameter.platform_version.name == "/platform/version/applications/demodjango/environment-pipelines"
    error_message = "SSM parameter name should be '/platform/version/applications/demodjango/environment-pipelines'"
  }

  assert {
    condition = aws_ssm_parameter.platform_version.tags == tomap({
      "application" : "demodjango",
      "pipeline" : "environment-pipelines",
      "managed-by" : "DBT Platform - Environment Pipelines Terraform",
    })
    error_message = "SSM parameter tags do not match expected values"
  }
}
