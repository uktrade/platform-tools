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
    condition     = aws_ssm_parameter.platform_version.name == "/platform/version/application/demodjango/environment/dev"
    error_message = "SSM parameter name should be '/platform/version/application/demodjango/environment/dev'"
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
    condition     = aws_ssm_parameter.platform_version.name == "/platform/version/application/demodjango/environment/dev/service/web"
    error_message = "SSM parameter name should be '/platform/version/application/demodjango/environment/dev/service/web'"
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
    condition     = aws_ssm_parameter.platform_version.name == "/platform/version/application/demodjango/codebase-pipeline"
    error_message = "SSM parameter name should be '/platform/version/application/demodjango/codebase-pipeline'"
  }

  assert {
    condition = aws_ssm_parameter.platform_version.tags == tomap({
      "application" : "demodjango",
      "pipeline" : "codebase-pipeline",
      "managed-by" : "DBT Platform - Codebase Pipeline Terraform",
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
    condition     = aws_ssm_parameter.platform_version.name == "/platform/version/application/demodjango/environment-pipeline"
    error_message = "SSM parameter name should be '/platform/version/application/demodjango/environment-pipeline'"
  }

  assert {
    condition = aws_ssm_parameter.platform_version.tags == tomap({
      "application" : "demodjango",
      "pipeline" : "environment-pipeline",
      "managed-by" : "DBT Platform - Environment Pipeline Terraform",
    })
    error_message = "SSM parameter tags do not match expected values"
  }
}
