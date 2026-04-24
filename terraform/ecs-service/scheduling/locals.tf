locals {


  full_service_name = var.name

  ### State Machine
  state_machine_definition = {
    Version        = "1.0"
    Comment        = "Run AWS Fargate task for Scheduled Job ${var.name}"
    TimeoutSeconds = var.timeout_seconds
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
              Subnets = var.subnet_ids
            }
            AssignPublicIp = "DISABLED"
            SecurityGroups = aws_security_group.job.id
          }
        }
        Retry = var.retries != null ? [{
          ErrorEquals = [
            "States.ALL"
          ]
          IntervalSeconds = 10 # do we want this value configurable?
          MaxAttempts     = var.retries
          BackoffRate     = 1.5 # do we want this value configurable?
        }] : []

        # notifications state

        End = true
      }
    }

    # include logic for notications here (or space for it!)
  }
}
