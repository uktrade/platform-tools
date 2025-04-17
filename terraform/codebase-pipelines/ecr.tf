resource "aws_ecr_repository" "this" {
  # checkov:skip=CKV_AWS_136:Not using KMS to encrypt repositories
  # checkov:skip=CKV_AWS_51:ECR image tags can't be immutable
  name = local.ecr_name

  tags = {
    copilot-pipeline    = var.codebase
    copilot-application = var.application
  }

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository_policy" "ecr_policy" {
  repository = aws_ecr_repository.this.name
  policy     = data.aws_iam_policy_document.ecr_policy.json
}

data "aws_iam_policy_document" "ecr_policy" {
  statement {
    effect = "Allow"

    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:CompleteLayerUpload",
      "ecr:GetDownloadUrlForLayer",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart"
    ]

    principals {
      type = "AWS"
      identifiers = [
        for id in local.deploy_account_ids :
        "arn:aws:iam::${id}:root"
      ]
    }
  }
}
