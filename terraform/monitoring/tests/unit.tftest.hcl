mock_provider "aws" {}

variables {
  vpc_name    = "test-vpc"
  application = "test-application"
  environment = "test-environment"
  config = {
    enable_ops_center = true
  }
  expected_tags = {
    application         = "test-application"
    environment         = "test-environment"
    managed-by          = "DBT Platform - Terraform"
    copilot-application = "test-application"
    copilot-environment = "test-environment"
  }
}

# Compute dashboard
run "test_compute_dashboard_is_created" {
  command = plan

  assert {
    condition     = aws_cloudwatch_dashboard.compute.dashboard_name == "test-application-test-environment-compute"
    error_message = "dashboard_name is incorrect"
  }

  # Test widgets are created
  # Not checking the whole queries as we would just have to replicate the code from the manifest, which would not add much value, so we're just going to check that the expected widgets exist.
  assert {
    condition     = jsondecode(aws_cloudwatch_dashboard.compute.dashboard_body).widgets[0].properties.title == "Deployed Application Images"
    error_message = "Deployed Application Images widget is not created"
  }

  assert {
    condition     = jsondecode(aws_cloudwatch_dashboard.compute.dashboard_body).widgets[1].properties.title == "Deployed Sidecar Images"
    error_message = "Deployed Sidecar Images widget is not created"
  }

  assert {
    condition     = jsondecode(aws_cloudwatch_dashboard.compute.dashboard_body).widgets[2].properties.title == "All Fargate Tasks Configuration and Consumption Details (CPU and Memory)"
    error_message = "Configuration and Consumption Details (CPU and Memory) widget is not created"
  }

  assert {
    condition     = jsondecode(aws_cloudwatch_dashboard.compute.dashboard_body).widgets[3].properties.title == "Top 10 Fargate Tasks with Optimization Opportunities (CPU)"
    error_message = "Optimization Opportunities (CPU) widget is not created"
  }

  assert {
    condition     = jsondecode(aws_cloudwatch_dashboard.compute.dashboard_body).widgets[4].properties.title == "Top 10 Fargate Tasks with Optimization Opportunities (Memory)"
    error_message = "Optimization Opportunities (Memory) widget is not created"
  }

  assert {
    condition     = jsondecode(aws_cloudwatch_dashboard.compute.dashboard_body).widgets[5].properties.title == "CPU Reserved Vs Avg Usage (All Fargate Tasks)"
    error_message = "CPU Reserved Vs Avg Usage widget is not created"
  }

  assert {
    condition     = jsondecode(aws_cloudwatch_dashboard.compute.dashboard_body).widgets[6].properties.title == "Memory Reserved Vs Avg Usage (All Fargate Tasks)"
    error_message = "Memory Reserved Vs Avg Usage widget is not created"
  }
}

# Application insights
run "test_application_insights_resource_group_is_created" {
  command = plan

  assert {
    condition     = aws_resourcegroups_group.application-insights-resources.name == "test-application-test-environment-application-insights-resources"
    error_message = "name is incorrect"
  }

  assert {
    condition     = aws_resourcegroups_group.application-insights-resources.resource_query[0].type == "TAG_FILTERS_1_0"
    error_message = "resource_query type is incorrect"
  }

  assert {
    condition = jsondecode(aws_resourcegroups_group.application-insights-resources.resource_query[0].query).ResourceTypeFilters == [
      "AWS::AllSupported"
    ]
    error_message = "ResourceTypeFilters is incorrect"
  }

  assert {
    condition = contains(
      jsondecode(aws_resourcegroups_group.application-insights-resources.resource_query[0].query).TagFilters,
      {
        Key    = "copilot-application"
        Values = ["test-application"]
      }
    )
    error_message = "Application TagFilter is incorrect"
  }

  assert {
    condition = contains(
      jsondecode(aws_resourcegroups_group.application-insights-resources.resource_query[0].query).TagFilters,
      {
        Key    = "copilot-environment"
        Values = ["test-environment"]
      }
    )
    error_message = "Environment TagFilter is incorrect"
  }

  assert {
    condition     = jsonencode(aws_resourcegroups_group.application-insights-resources.tags) == jsonencode(var.expected_tags)
    error_message = "Expected: ${jsonencode(var.expected_tags)}\nActual:   ${jsonencode(aws_resourcegroups_group.application-insights-resources.tags)}"
  }
}

run "test_application_insights_application_is_created" {
  command = plan

  assert {
    condition     = aws_applicationinsights_application.application-insights.resource_group_name == "test-application-test-environment-application-insights-resources"
    error_message = "resource_group_name is incorrect"
  }

  assert {
    condition     = aws_applicationinsights_application.application-insights.auto_config_enabled == true
    error_message = "Should be: true"
  }

  assert {
    condition     = aws_applicationinsights_application.application-insights.ops_center_enabled == true
    error_message = "Should be: true"
  }

  assert {
    condition     = jsonencode(aws_applicationinsights_application.application-insights.tags) == jsonencode(var.expected_tags)
    error_message = "Expected: ${jsonencode(var.expected_tags)}\nActual:   ${jsonencode(aws_applicationinsights_application.application-insights.tags)}"
  }
}

run "test_application_insights_application_can_be_created_with_ops_center_disabled" {
  command = plan

  variables {
    config = {
      enable_ops_center = false
    }
  }

  assert {
    condition     = aws_applicationinsights_application.application-insights.ops_center_enabled == false
    error_message = "Should be: false"
  }
}
