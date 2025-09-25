resource "aws_sns_topic" "guardduty_notifications" {
  count = try(var.config.guardduty_malware_protection.enabled, false) ? 1 : 0

  name = "${var.application}-${var.environment}-guardduty-notifications"
  tags = local.tags
}

resource "aws_iam_role" "event_bridge_guardduty" {
  count = try(var.config.guardduty_malware_protection.enabled, false) ? 1 : 0

  name = "${var.application}-${var.environment}-guardduty-eventbridge"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "events.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = local.tags
}

resource "aws_iam_role_policy" "event_bridge_guardduty_policy" {
  count = try(var.config.guardduty_malware_protection.enabled, false) ? 1 : 0

  name = "${var.application}-${var.environment}-guardduty-eventbridge-policy"
  role = aws_iam_role.event_bridge_guardduty[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.guardduty_notifications[0].arn
      }
    ]
  })
}

resource "aws_cloudwatch_event_rule" "guardduty_findings" {
  count = try(var.config.guardduty_malware_protection.enabled, false) ? 1 : 0

  name        = "${var.application}-${var.environment}-guardduty-findings"
  description = "Capture GuardDuty malware findings for ${var.application}-${var.environment}"

  event_pattern = jsonencode({
    source      = ["aws.guardduty"]
    detail-type = ["GuardDuty Finding"]
    detail = {
      type = ["Malware Protection"]
    }
  })

  depends_on = [data.aws_guardduty_detector.existing]
}

resource "aws_cloudwatch_event_target" "guardduty_findings_sns" {
  count = try(var.config.guardduty_malware_protection.enabled, false) ? 1 : 0

  rule      = aws_cloudwatch_event_rule.guardduty_findings[0].name
  target_id = "GuardDutyToSNS"
  arn       = aws_sns_topic.guardduty_notifications[0].arn
  role_arn  = aws_iam_role.event_bridge_guardduty[0].arn
}

resource "aws_sns_topic_subscription" "guardduty_email" {
  count = try(var.config.guardduty_malware_protection.enabled, false) ? 1 : 0

  topic_arn = aws_sns_topic.guardduty_notifications[0].arn
  protocol  = "email"
  endpoint  = "sre@businessandtrade.gov.uk"
}