resource "aws_appautoscaling_target" "ecs_autoscaling" {
  for_each           = toset(local.is_scheduled_job ? [] : ["enabled"])
  service_namespace  = "ecs"
  resource_id        = "service/${data.aws_ecs_cluster.cluster.cluster_name}/${local.full_service_name}"
  scalable_dimension = "ecs:service:DesiredCount"

  min_capacity = local.count_min
  max_capacity = local.count_max

  depends_on = [
    aws_ecs_service.service["enabled"]
  ]
}

moved {
  from = aws_appautoscaling_target.ecs_autoscaling
  to   = aws_appautoscaling_target.ecs_autoscaling["enabled"]
}

resource "aws_appautoscaling_scheduled_action" "scheduled_autoscaling" {
  for_each = local.scheduled_actions

  name               = each.key
  service_namespace  = aws_appautoscaling_target.ecs_autoscaling["enabled"].service_namespace
  resource_id        = aws_appautoscaling_target.ecs_autoscaling["enabled"].resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_autoscaling["enabled"].scalable_dimension

  schedule = "cron(${each.value.schedule})"
  timezone = "Europe/London"


  scalable_target_action {
    min_capacity = each.value.min
    max_capacity = each.value.max
  }
}

resource "aws_appautoscaling_policy" "cpu_autoscaling_policy" {
  count = local.enable_cpu ? 1 : 0

  name               = "${local.full_service_name}-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.ecs_autoscaling["enabled"].service_namespace
  resource_id        = aws_appautoscaling_target.ecs_autoscaling["enabled"].resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_autoscaling["enabled"].scalable_dimension

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = local.cpu_value
    scale_in_cooldown  = local.cpu_cool_in
    scale_out_cooldown = local.cpu_cool_out
  }
}

resource "aws_appautoscaling_policy" "memory_autoscaling_policy" {
  count = local.enable_mem ? 1 : 0

  name               = "${local.full_service_name}-memory-autoscaling"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.ecs_autoscaling["enabled"].service_namespace
  resource_id        = aws_appautoscaling_target.ecs_autoscaling["enabled"].resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_autoscaling["enabled"].scalable_dimension

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value       = local.mem_value
    scale_in_cooldown  = local.mem_cool_in
    scale_out_cooldown = local.mem_cool_out
  }
}

# Look up the ALB that is attached to the TG (after the listener-rule Lambda runs)
data "aws_lb" "load_balancer" {
  count = local.enable_req ? 1 : 0
  arn   = one(aws_lb_target_group.target_group[0].load_balancer_arns)

  # Ensure the listener-rule lambda runs first to attach the target group on the ALB
  depends_on = [
    aws_lambda_invocation.dummy_listener_rule
  ]
}

# This policy is only for 'Load Balanced Web Service' type services
resource "aws_appautoscaling_policy" "requests_autoscaling_policy" {
  count = local.enable_req ? 1 : 0

  name               = "${local.full_service_name}-req-100"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.ecs_autoscaling["enabled"].service_namespace
  resource_id        = aws_appautoscaling_target.ecs_autoscaling["enabled"].resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_autoscaling["enabled"].scalable_dimension

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      # Very specific format required: app/<load-balancer-name>/<load-balancer-id>/targetgroup/<target-group-name>/<target-group-id>
      # See AWS docs: https://docs.aws.amazon.com/autoscaling/plans/APIReference/API_PredefinedScalingMetricSpecification.html
      resource_label = "${data.aws_lb.load_balancer[0].arn_suffix}/${aws_lb_target_group.target_group[0].arn_suffix}"
    }
    target_value       = local.req_value
    scale_in_cooldown  = local.req_cool_in
    scale_out_cooldown = local.req_cool_out
  }
}
