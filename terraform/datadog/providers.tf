terraform {
  required_providers {
    datadog = {
      source                = "DataDog/datadog"
      configuration_aliases = [datadog.ddog]
    }
  }
}

