locals {
  tags = {
    Name       = "terraform-statefile-${var.aws_account_name}"
    managed-by = "Terraform"
  }
}
