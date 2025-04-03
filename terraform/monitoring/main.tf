resource "aws_cloudwatch_dashboard" "compute" {
  dashboard_name = "${var.application}-${var.environment}-compute"
  dashboard_body = jsonencode({
    widgets : [
      {
        height : 7,
        width : 24,
        y : 0,
        x : 0,
        type : "log",
        properties : {
          query : "SOURCE '/aws/ecs/containerinsights/${var.application}-${var.environment}/performance' | fields fromMillis(Timestamp) as Time, ClusterName as Cluster, TaskDefinitionFamily as Service, ContainerName as Container, Image\n| filter @message like '${var.application}/'\n| sort Cluster, Service, Container\n| dedup Service, Container",
          region : "eu-west-2",
          stacked : false,
          title : "Deployed Application Images",
          view : "table"
        }
      },
      {
        height : 7,
        width : 24,
        y : 7,
        x : 0,
        type : "log",
        properties : {
          query : "SOURCE '/aws/ecs/containerinsights/${var.application}-${var.environment}/performance' | fields fromMillis(Timestamp) as Time, ClusterName as Cluster, TaskDefinitionFamily as Service, ContainerName as Container, Image\n| filter @message like '\"Image\":'\n| filter @message not like '${var.application}/'\n| sort Cluster, Service, Container\n| dedup Service, Container",
          region : "eu-west-2",
          stacked : false,
          title : "Deployed Sidecar Images",
          view : "table"
        }
      },
      {
        height : 7,
        width : 24,
        y : 14,
        x : 0,
        type : "log",
        properties : {
          query : "SOURCE '/aws/ecs/containerinsights/${var.application}-${var.environment}/performance' | fields @message\n| filter Type=\"Task\"\n| filter @logStream like /FargateTelemetry/\n| stats latest(TaskDefinitionFamily) as TaskDefFamily, \n        latest(TaskDefinitionRevision) as Rev, \n        max(CpuReserved) as TaskCpuReserved, \n        avg(CpuUtilized) as AvgCpuUtilized, \n        concat(ceil(avg(CpuUtilized) * 100 / TaskCpuReserved),\" %\") as AvgCpuUtilizedPerc, \n        max(CpuUtilized) as PeakCpuUtilized, \n        concat(ceil(max(CpuUtilized) * 100 / TaskCpuReserved),\" %\") as PeakCpuUtilizedPerc, \n        max(MemoryReserved) as TaskMemReserved, \n        ceil(avg(MemoryUtilized)) as AvgMemUtilized, \n        concat(ceil(avg(MemoryUtilized) * 100 / TaskMemReserved),\" %\") as AvgMemUtilizedPerc, \n        max(MemoryUtilized) as PeakMemUtilized, \n        concat(ceil(max(MemoryUtilized) * 100 / TaskMemReserved),\" %\") as PeakMemUtilizedPerc \n        by TaskId\n| sort TaskDefFamily asc\n",
          region : "eu-west-2",
          stacked : false,
          title : "All Fargate Tasks Configuration and Consumption Details (CPU and Memory)",
          view : "table"
        }
      },
      {
        height : 6,
        width : 15,
        y : 21,
        x : 0,
        type : "log",
        properties : {
          query : "SOURCE '/aws/ecs/containerinsights/${var.application}-${var.environment}/performance' | fields @message\n| filter Type=\"Task\"\n| filter @logStream like /FargateTelemetry/\n| stats latest(TaskDefinitionFamily) as TaskDefFamily, latest(ServiceName) as SvcName, concat(floor((max(CpuReserved) - avg(CpuUtilized)) * 100 / max(CpuReserved)), \" %\") as AvgCpuWastePercentage by TaskId\n| sort AvgCpuWastePercentage desc\n| limit 10",
          stacked : false,
          title : "Top 10 Fargate Tasks with Optimization Opportunities (CPU)",
          view : "table"
        }
      },
      {
        height : 6,
        width : 15,
        y : 27,
        x : 0,
        type : "log",
        properties : {
          query : "SOURCE '/aws/ecs/containerinsights/${var.application}-${var.environment}/performance' | fields @message\n| filter Type=\"Task\"\n| filter @logStream like /FargateTelemetry/\n| stats latest(TaskDefinitionFamily) as TaskDefFamily, latest(ServiceName) as SvcName, concat(floor((max(MemoryReserved) - avg(MemoryUtilized)) * 100 / max(MemoryReserved)), \" %\") as AvgMemWastePercentage by TaskId\n| sort AvgMemWastePercentage desc\n| limit 10",
          stacked : false,
          title : "Top 10 Fargate Tasks with Optimization Opportunities (Memory)",
          view : "table"
        }
      },
      {
        height : 6,
        width : 9,
        y : 21,
        x : 15,
        type : "log",
        properties : {
          query : "SOURCE '/aws/ecs/containerinsights/${var.application}-${var.environment}/performance' | fields @message\n| filter Type = \"Task\"\n| filter @logStream like /FargateTelemetry/\n| stats count_distinct(TaskId) as TotalTasks, avg(CpuReserved) * TotalTasks as TotalCPUReserved, avg(CpuUtilized) * TotalTasks as AvgCPUConsumed by bin(15m) \n",
          region : "eu-west-2",
          stacked : false,
          title : "CPU Reserved Vs Avg Usage (All Fargate Tasks)",
          view : "timeSeries"
        }
      },
      {
        height : 6,
        width : 9,
        y : 27,
        x : 15,
        type : "log",
        properties : {
          query : "SOURCE '/aws/ecs/containerinsights/${var.application}-${var.environment}/performance' | fields @message\n| filter Type = \"Task\"\n| filter @logStream like /FargateTelemetry/\n| stats count_distinct(TaskId) as TotalTasks, avg(MemoryReserved) * TotalTasks as TotalMemReserved, avg(MemoryUtilized) * TotalTasks as AvgMemConsumed by bin(30m) \n",
          stacked : false,
          title : "Memory Reserved Vs Avg Usage (All Fargate Tasks)",
          view : "timeSeries"
        }
      }
    ]
  })
  # Tags are not supported: https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_dashboard#argument-reference
}

resource "aws_resourcegroups_group" "application-insights-resources" {
  name = "${var.application}-${var.environment}-application-insights-resources"
  resource_query {
    type = "TAG_FILTERS_1_0"
    query = jsonencode({
      ResourceTypeFilters = ["AWS::AllSupported"]
      TagFilters = [
        {
          Key    = "copilot-application"
          Values = [var.application]
        },
        {
          Key    = "copilot-environment"
          Values = [var.environment]
        }
      ]
    })
  }
  tags = local.tags
}

resource "aws_applicationinsights_application" "application-insights" {
  resource_group_name = aws_resourcegroups_group.application-insights-resources.name
  auto_config_enabled = true
  ops_center_enabled  = var.config.enable_ops_center
  tags                = local.tags
}
