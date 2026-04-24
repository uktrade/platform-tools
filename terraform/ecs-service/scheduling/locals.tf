locals {


  full_service_name = var.name

  # timeout_seconds = lookup(var.timeout, "timeout", 86400) # TODO: figure out why lookup() breaks the test_state_machine_definition_has_no_timeout test
  timeout_seconds = var.timeout != null ? var.timeout : 86400 # set timeout to 24 hours to avoid runaway state machines caused by the default provided by AWS (99999999, which is approximately 3 years). See here: https://docs.aws.amazon.com/step-functions/latest/dg/state-task.html

  ### State Machine
  state_machine_definition = {
    Version        = "1.0"
    Comment        = "Run AWS Fargate task for Scheduled Job ${var.name}"
    TimeoutSeconds = local.timeout_seconds
    StartAt        = "run-fargate-task"
    States = {
      run-fargate-task = {
        Type     = "Task"
        Resource = "arn:aws:states:::ecs:runTask.sync"
        Parameters = {
          LaunchType      = "FARGATE"
          PlatformVersion = "LATEST"
          Cluster         = var.cluster_id
          TaskDefinition  = "" # Replace with aws_ecs_task_definition.service.arn
          PropagateTags   = "TASK_DEFINITION"
          "Group.$"       = "$$.Execution.Name"
          NetworkConfiguration = {
            AwsvpcConfiguration = {
              Subnets = var.subnet_ids
            }
            AssignPublicIp = "DISABLED"
            SecurityGroups = var.security_group_id
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
