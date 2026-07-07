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
      "ecr:GetDownloadUrlForLayer",
    ]

    principals {
      type = "AWS"
      identifiers = [
        for id in local.deploy_account_ids :
        "arn:aws:iam::${id}:root"
      ]
    }
  }

  statement {
    effect = "Allow"
    sid    = "allowECRAuthentication"
    actions = [
      "ecr:GetAuthorizationToken"
    ]
    resources = "*"
  }

  statement {
    sid    = "AllowImagePull"
    effect = "Allow"
    actions = [
      "ecr:BatchGetImage",
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer"
    ]
    resources = [
      "arn:aws:ecr:eu-west-2:${id}:repository/${locals.ecr_name}",
    ]
  }

  statement {
    sid    = "AllowSignatureRevokeCheck"
    effect = "Allow"
    actions = [
      "signer:GetRevocationStatus"
    ]
    resources = [
      "*"
    ]
  }

  statement {
    effect = "Allow"
    sid    = "PushActions"

    actions = [
      "ecr:CompleteLayerUpload",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart"
    ]

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    condition {
      test     = "StringLike"
      variable = "aws:PrincipalArn"
      values = [
        "arn:aws:iam::${id}:role/aws-reserved/sso.amazonaws.com/eu-west-2/AWSReservedSSO_AdministratorAccess_*",
        "arn:aws:iam::${id}:role/GithubActionsRole" #Replace me once you know the role it should be!
      ]
    }
  }

  statement {
    sid    = "PreventRepoDelete"
    effect = "Deny"

    actions = [
      "ecr:DeleteRepository"
    ]

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }
  }

  statement {
    sid    = "PreventImageDelete"
    effect = "Deny"

    actions = [
      "ecr:BatchDeleteImage"
    ]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "ArnNotLike"
      variable = "aws:PrincipalArn"
      values   = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/ecr-housekeeping-role"]
    }
  }
}
