locals {
  tags = {
    application = var.application
    environment = var.environment
    managed-by  = "DBT Platform - Environment Terraform"
  }

  cluster_name = "${var.application}-${var.environment}-cluster"
  sg_env_tags = merge(local.tags, {
    Name = "platform-${var.application}-${var.environment}-env-sg"
    }
  )

  vpc_peering_by_name = {
    for name, value in zipmap(
      data.aws_ssm_parameters_by_path.vpc_peering.names,
      data.aws_ssm_parameters_by_path.vpc_peering.values
    ) : name => jsondecode(value)
  }

  # Only keep those meant for this environment's security group
  vpc_peering_for_this_sg = {
    for name, value in local.vpc_peering_by_name :
    name => value
    if value["security-group-id"] == aws_security_group.environment_security_group.id
  }
}
