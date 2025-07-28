resource "aws_cloudwatch_event_rule" "ecr_image_publish" {
  for_each    = local.pipeline_map
  name        = "${var.application}-${var.codebase}-publish-${each.value.name}"
  description = "Trigger ${each.value.name} deploy pipeline when an ECR image is published"

  event_pattern = jsonencode({
    source : ["aws.ecr"],
    detail-type : ["ECR Image Action"],
    detail : {
      action-type : ["PUSH"],
      image-tag : strcontains(each.value.image_tag, "*") ? [{wildcard : each.value.image_tag}] : [each.value.image_tag],
      repository-name : [local.ecr_name],
      result : ["SUCCESS"],
    }
  })
}

resource "aws_cloudwatch_event_target" "codepipeline" {
  for_each = local.pipeline_map
  rule     = aws_cloudwatch_event_rule.ecr_image_publish[each.key].name
  arn      = aws_codepipeline.codebase_pipeline[each.key].arn
  role_arn = aws_iam_role.event_bridge_pipeline_trigger[""].arn
}

resource "aws_iam_role" "event_bridge_pipeline_trigger" {
  for_each           = toset(length(local.pipeline_map) > 0 ? [""] : [])
  name               = "${var.application}-${var.codebase}-pipeline-trigger"
  assume_role_policy = data.aws_iam_policy_document.assume_event_bridge_policy.json
  tags               = local.tags
}

resource "aws_iam_role_policy" "event_bridge_pipeline_trigger" {
  for_each = toset(length(local.pipeline_map) > 0 ? [""] : [])
  name     = "event-bridge-access"
  role     = aws_iam_role.event_bridge_pipeline_trigger[""].name
  policy   = data.aws_iam_policy_document.event_bridge_pipeline_trigger.json
}

data "aws_iam_policy_document" "assume_event_bridge_policy" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "event_bridge_pipeline_trigger" {
  dynamic "statement" {
    for_each = local.pipeline_map
    content {
      effect = "Allow"
      actions = [
        "codepipeline:StartPipelineExecution"
      ]
      resources = [
        "arn:aws:codepipeline:${local.account_region}:${var.application}-${var.codebase}-${statement.value.name}-codebase"
      ]
    }
  }
}
