locals {
  tags = {
    Name       = "terraform-statefile-${var.aws_account_name}"
    managed-by = "Terraform"
  }

  key_policy_role_name_suffix = var.key_policy_role_name_suffix != null ? var.key_policy_role_name_suffix : var.aws_account_name
}
