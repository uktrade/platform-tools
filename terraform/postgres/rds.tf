resource "aws_db_parameter_group" "default" {
  name   = "${local.name}-${local.family}"
  family = local.family

  tags = local.tags

  parameter {
    name  = "client_encoding"
    value = "utf8"
  }

  parameter {
    name  = "log_statement"
    value = "ddl"
  }

  parameter {
    name  = "log_statement_sample_rate"
    value = "1.0"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_db_subnet_group" "default" {
  name       = local.name
  subnet_ids = data.aws_subnets.private-subnets.ids

  tags = local.tags
}

resource "aws_kms_key" "default" {
  description         = "${local.name} KMS key"
  enable_key_rotation = true

  policy = jsonencode({
    Id = "key-default-1"
    Statement = [
      {
        "Sid" : "Enable IAM User Permissions",
        "Effect" : "Allow",
        "Principal" : {
          "AWS" : "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        },
        "Action" : "kms:*",
        "Resource" : "*"
      }
    ]
    Version = "2012-10-17"
  })
}

resource "aws_db_instance" "default" {
  # checkov:skip=CKV_AWS_354:Performance Insights key cannot be changed once the database has been created. (https://github.com/hashicorp/terraform-provider-aws/issues/9399)
  # checkov:skip=CKV_AWS_161:Significant upstream impact to other components
  identifier = local.name

  db_name                     = "main"
  username                    = "postgres"
  manage_master_user_password = true
  multi_az                    = local.multi_az

  # version
  engine         = "postgres"
  engine_version = local.version
  instance_class = local.instance_class

  # upgrades
  allow_major_version_upgrade = true
  auto_minor_version_upgrade  = true
  apply_immediately           = coalesce(var.config.apply_immediately, false)
  maintenance_window          = "Mon:00:00-Mon:03:00"

  # storage
  allocated_storage = local.volume_size
  storage_encrypted = true
  kms_key_id        = aws_kms_key.default.arn
  storage_type      = local.storage_type
  iops              = local.iops

  parameter_group_name = aws_db_parameter_group.default.name
  db_subnet_group_name = aws_db_subnet_group.default.name

  backup_retention_period = local.backup_retention_days
  backup_window           = "07:00-09:00"
  deletion_protection     = local.deletion_protection

  vpc_security_group_ids              = [aws_security_group.default.id]
  publicly_accessible                 = false
  iam_database_authentication_enabled = false

  snapshot_identifier       = local.snapshot_id
  skip_final_snapshot       = local.skip_final_snapshot
  final_snapshot_identifier = local.final_snapshot_identifier
  copy_tags_to_snapshot     = true

  enabled_cloudwatch_logs_exports = ["postgresql"]

  # monitoring and performance
  performance_insights_enabled          = true
  performance_insights_retention_period = 7
  monitoring_interval                   = 15
  monitoring_role_arn                   = aws_iam_role.enhanced-monitoring.arn

  depends_on = [
    aws_db_subnet_group.default,
    aws_security_group.default,
    aws_db_parameter_group.default,
  ]

  tags = local.tags
}

resource "aws_iam_role" "enhanced-monitoring" {
  name_prefix        = "rds-enhanced-monitoring-"
  assume_role_policy = data.aws_iam_policy_document.enhanced-monitoring.json
}

resource "aws_iam_role_policy_attachment" "enhanced-monitoring" {
  role       = aws_iam_role.enhanced-monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

data "aws_iam_policy_document" "enhanced-monitoring" {
  statement {
    actions = [
      "sts:AssumeRole",
    ]

    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["monitoring.rds.amazonaws.com"]
    }
  }
}
