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
