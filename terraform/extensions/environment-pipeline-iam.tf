resource "aws_iam_role" "environment_pipeline_deploy" {
  name               = "${var.args.application}-${var.environment}-environment-pipeline-deploy"
  assume_role_policy = data.aws_iam_policy_document.assume_environment_pipeline.json
  tags               = local.tags
}

data "aws_iam_policy_document" "assume_environment_pipeline" {
  statement {
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${local.pipeline_account_id}:root"]
    }
    condition {
      test = "ArnLike"
      values = [
        "arn:aws:iam::${local.pipeline_account_id}:role/${var.args.application}-*-environment-*"
      ]
      variable = "aws:PrincipalArn"
    }
    actions = ["sts:AssumeRole"]
  }
}
