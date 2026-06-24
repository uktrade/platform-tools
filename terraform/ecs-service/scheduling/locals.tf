locals {
  schedule_expression = can(regex("minutes|hours|days", var.schedule)) ? "rate(${var.schedule})" : "cron(${var.schedule})"

  full_service_name = var.name

  cluster_name = split("/", var.cluster_id)[1]

  ### State Machine
  state_machine_definition = {
    Version        = "1.0"
    Comment        = "Run AWS Fargate task for Scheduled Job ${var.name}"
    TimeoutSeconds = var.timeout_seconds != null ? var.timeout_seconds : 86400 # set timeout to 24 hours to avoid runaway state machines caused by the default provided by AWS (99999999, which is approximately 3 years). See here: https://docs.aws.amazon.com/step-functions/latest/dg/state-task.html
    StartAt        = "run-fargate-task"
    States = {
      run-fargate-task = {
        Type     = "Task"
        Resource = "arn:aws:states:::ecs:runTask.sync"
        Parameters = {
          LaunchType      = "FARGATE"
          PlatformVersion = "LATEST"
          Cluster         = var.cluster_id
          TaskDefinition  = var.task_definition_arn
          PropagateTags   = "TASK_DEFINITION"
          "Group.$"       = "$$.Execution.Name"
          NetworkConfiguration = {
            AwsvpcConfiguration = {
              Subnets        = var.subnet_ids
              AssignPublicIp = "DISABLED"
              SecurityGroups = [aws_security_group.scheduled_job.id]
            }
          }
        }
        Retry = var.retries != null ? [{
          ErrorEquals = [
            "States.ALL"
          ]
          IntervalSeconds = 10
          MaxAttempts     = var.retries
          BackoffRate     = 1.5
        }] : []

        # notifications state

        End = true
      }
    }

    # include logic for notications here (or space for it!)
  }
}
