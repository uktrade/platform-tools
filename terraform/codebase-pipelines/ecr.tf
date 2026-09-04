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

      values = [
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/ecr-housekeeping-role",
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/github-oidc-${var.application}-platform-image-build",
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/github-oidc-${var.application}-repo-role" #TODO - Remove once all BYOD/scheduled job image build workflows no longer use this IAM role
      ]
    }
  }

  statement {
    sid    = "ImagePull"
    effect = "Allow"
    actions = [
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
    ]
    principals {
      type = "AWS"
      identifiers = [
        for id in local.deploy_account_ids : "arn:aws:iam::${id}:root"
      ]
    }
  }

  dynamic "statement" {
    for_each = !(var.pipeline_mode == "github_actions" && var.requires_image_build == false) ? [1] : []

    content {
      sid    = "DefaultImagePush"
      effect = "Allow"
      actions = [
        "ecr:BatchCheckLayerAvailability",
        "ecr:CompleteLayerUpload",
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

  dynamic "statement" {
    for_each = (var.pipeline_mode == "github_actions" && var.requires_image_build == false) ? [1] : []

    content {
      sid    = "RestrictedImagePushAllow"
      effect = "Allow"
      actions = [
        "ecr:CompleteLayerUpload",
        "ecr:InitiateLayerUpload",
        "ecr:PutImage",
        "ecr:UploadLayerPart",
        "ecr:BatchCheckLayerAvailability"
      ]
      principals {
        type = "AWS"
        identifiers = [
          for id in local.deploy_account_ids :
          "arn:aws:iam::${id}:root"
        ]
      }
      condition {
        test     = "ArnLike"
        variable = "aws:PrincipalArn"
        values = concat(
          flatten([
            for id in local.deploy_account_ids : [
              "arn:aws:iam::${id}:role/github-oidc-${var.application}-repo-role" # TODO: Remove once all BYOD/scheduled job image build workflows no longer use this IAM role
            ]
          ]),
          [
            "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/aws-reserved/sso.amazonaws.com/eu-west-2/AWSReservedSSO_AdministratorAccess_*",
            "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/github-oidc-${var.application}-platform-image-build"
          ]
        )
      }
    }
  }

  dynamic "statement" {
    for_each = (var.pipeline_mode == "github_actions" && var.requires_image_build == false) ? [1] : []

    content {
      sid    = "RestrictedImagePushDeny"
      effect = "Deny"
      actions = [
        "ecr:CompleteLayerUpload",
        "ecr:InitiateLayerUpload",
        "ecr:PutImage",
        "ecr:UploadLayerPart",
        "ecr:BatchCheckLayerAvailability"
      ]
      principals {
        type        = "AWS"
        identifiers = ["*"]
      }
      condition {
        test     = "ArnNotLike"
        variable = "aws:PrincipalArn"
        values = concat(
          flatten([
            for id in local.deploy_account_ids : [
              "arn:aws:iam::${id}:role/github-oidc-${var.application}-repo-role" # TODO: Remove once all BYOD/scheduled job image build workflows no longer use this IAM role
            ]
          ]),
          [
            "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/aws-reserved/sso.amazonaws.com/eu-west-2/AWSReservedSSO_AdministratorAccess_*",
            "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/github-oidc-${var.application}-platform-image-build"
          ]
        )
      }
    }
  }
}