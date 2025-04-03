# Terraform used by Platform-tools

## Setup

```shell
   pip install poetry && poetry install && poetry run pre-commit install
```

## Trufflehog pre-commit hook

- Installation on Mac

```shell
brew install trufflehog
```

Alternative installation methods [here](https://github.com/trufflesecurity/trufflehog)

## Testing / quality checks

Various quality checks are run in AWS Codebuild in the `platform-tools` account for any push to a pull request branch:

- [Checkov](https://www.checkov.io/)
- [terraform fmt](https://developer.hashicorp.com/terraform/cli/commands/fmt)
- [terraform validate](https://developer.hashicorp.com/terraform/cli/commands/validate)
- [tflint](https://github.com/terraform-linters/tflint])
- [terraform test](https://developer.hashicorp.com/terraform/cli/commands/test) - plan style
- python tests - unit tests for python code within the terraform modules

- Todo: [terraform test](https://developer.hashicorp.com/terraform/cli/commands/test) - end to end tests which do an apply and actually provision infrastructure

### Running the terraform unit tests locally

Ensure that local variable `AWS_PROFILE` is set to `sandbox` and that you have run:

```shell
aws sso login
```

The faster, but less comprehensive, tests that run against the `terraform plan` for a module can be run by `cd`-ing into the module folder and running:

```shell
terraform test
```

To run the longer end-to-end tests that actually deploy the module (via `terraform apply`), perform assertions and tear back down are run from the same directory as follows:

```shell
terraform test -test-directory e2e-tests
```

### Running the python unit tests locally

The Lambda provisioned by the terraform postgres module uses python 3.11 at runtime. Tests should be executed locally, using python 3.11. From the root directory, check which python version the poetry environment is using:

```shell
poetry run python --version
```

If it is not 3.11, run

```shell
poetry env use python3.11
```

(python 3.11 must be installed)

Install dependencies:

```shell
poetry install
```

Execute the tests:

```shell
poetry run pytest
```

### End to end testing

Because this codebase is only fully exercised in conjunction with several others, we have [platform-end-to-end-tests](https://github.com/uktrade/platform-end-to-end-tests), which orchestrates the testing of them working together.

## Backing services module

This module is configured by a YAML file and two simple args:

```terraform
locals {
  args = {
    application = "my-app-tf"
    services    = yamldecode(file("platform-config.yml"))
  }
}

module "extensions" {
  source     = "git::ssh://git@github.com/uktrade/platform-tools.git//terraform/extensions?depth=1&ref=main"

  args        = local.args
  environment = "my-env"
  vpc_name    = "my-vpc-name"
}
```

## Opensearch module configuration options

The options available for configuring the opensearch module should be applied in the `platform-config.yml` file. They
should look something like this:

```yaml
my-opensearch:
  type: opensearch
  environments:
    '*': # Default configuration values
      plan: small
      engine: '2.11'
      ebs_volume_type: gp3 # Optional. Must be one of: standard, gp2, gp3, io1, io2, sc1 or st1. Defaults to gp2.
      ebs_throughput: 500 # Optional. Throughput in MiB/s. Only relevant for volume type gp3. Defaults to 250 MiB/s.
      index_slow_log_retention_in_days: 3 # Optional. Valid values can be found here: https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_group#retention_in_days
      search_slow_log_retention_in_days: 14 # Optional. As above.
      es_app_log_retention_in_days: 30 # Optional. As above.
      audit_log_retention_in_days: 1096 # Optional. As above.
      # The following are derived from the plan. DBTP-841 will allow them to be overriden here.
      #    volume_size: 1000
      #    instances: 1
      #    master: false
      #    instance: m6g.xlarge.search
    env-one: # Per-environment overrides for any of the defaults in the previous section
      plan: large # Override the plan.
      engine: '2.7' # Downgrade the engine.
```

## Application Load Balancer module

This module will create a ALB that lets you specify multiple domain names for use in the HTTPS listener rule. In addition it will create the required certificates for all the domains specified.

The primary domain will always follow the pattern:

For non-production: `internal.<application_name>.uktrade.digital`

For production: `internal.<application_name>.prod.uktrade.digital`

If there are multiple web services on the application, you can add the additional domain to your certificate by adding the prefix name (eg. `internal.static`) to the variable `additional_address_list` see extension.yml example below. `Note: this is just the prefix, no need to add env.uktrade.digital`

`cdn_domains_list` and `additional_address_list` are optional.

### Route 53 record creation

The R53 domains for non-production and production are stored in different AWS accounts. The last half of the Terraform code needs to be able to run in the correct AWS account. This is determined by the provider passed in from the `<application>-deploy` `aws-domain` alias.

example `platform-config.yml` config.

```yaml
my-application-alb:
  type: alb
  environments:
    dev:
      additional_address_list:
        - internal.my-web-service-2
```

## CDN

This module will create the CloudFront (CDN) endpoints for the application if enabled.

`cdn_domains_list` is a map of the domain names that will be configured in CloudFront.

- the key is the fully qualified domain name.
- the value is an array containing the internal prefix and the base domain (the application's Route 53 zone).

### Optional settings:

To create a R53 record pointing to the CloudFront endpoint, set this to true. If not set, in non production this is set to true by default and set to false in production.

- enable_cdn_record: true

To turn on CloudFront logging to a S3 bucket, set this to true.

- enable_logging: true

Add this property to change the CloudFront `custom_read_timeout` value (defaults to 30 seconds):

- cdn_timeout_seconds: 60

example `platform-config.yml` config.

```yaml
my-application-alb:
  type: alb
  environments:
    dev:
      cdn_domains_list:
        - dev.my-application.uktrade.digital:
            ['internal', 'my-application.uktrade.digital']
        - dev.my-web-service-2.my-application.uktrade.digital:
            ['internal.my-web-service-2', 'my-application.uktrade.digital']
      additional_address_list:
        - internal.my-web-service-2
      enable_cdn_record: false
      enable_logging: true
      cdn_timeout_seconds: 60
    prod:
      cdn_domains_list:
        - my-application.prod.uktrade.digital:
            ['internal', 'my-application.prod.uktrade.digital']
```

## Monitoring

This will provision a CloudWatch Compute Dashboard and Application Insights for `<application>-<environment>`.

Example usage in `platform-config.yml`...

```yaml
demodjango-monitoring:
  type: monitoring
  environments:
    '*':
      enable_ops_center: false
    prod:
      enable_ops_center: true
```

## S3 bucket

An s3 bucket can be added by configuring the `platform-config.yml` file. Below is an example configuration, showing the available options:

```yaml
my-s3-bucket:
  type: s3
  readonly: false # Optional
  services: # Optional
    - 'web'
  environments:
    '*': # Default configuration values
      bucket_name: my-bucket-dev # Mandatory
      retention_policy: # Optional
        mode: COMPLIANCE # GOVERNANCE" or "COMPLIANCE"
        days: 10 # Integer value.  Alternatively years may be specified.
      versioning: true # Optional
      lifecycle_rules: # Optional.  If present, contains a list of rules.
        - filter_prefix: 'bananas/' # Optional.  If none, the rule applies to all objects. Use an empty string for a catch-all rule.
          expiration_days: 10 # Integer value
          enabled: true # Mandatory flag
  objects: # Optional.  If present, contains a list of objects
    - key: healthcheck.txt # Mandatory
      body: | # Optional
        HEALTHCHECK WORKS!
```

## Postgres database

A postgres database can be added by configuring the `platform-config.yml` file. Below is a simple example configuration, showing some of the available options:

```yaml
my-postgres-db:
  type: postgres
  version: 16
  environments:
    '*':
      plan: tiny
      backup_retention_days: 1 # Optional.  Must be between 1 and 35. Defaults to 7.
    prod:
      deletion_protection: true # Optional
```

## S3 to S3 data migration module

This module will create cross account permissions to write to your S3 bucket, allowing the copying of files from a source S3 bucket to your destination S3 bucket. Any cross account data migration **must be approved by cyber**. Please see the [S3 to S3 data migration documentation](https://platform.readme.trade.gov.uk/reference/cross-account-s3-to-s3-data-migration/) for further details on using this module.

Most users will not have permissions to apply the following configuration.  In this case, an SRE team member or someone from the DBT-platform team will be able to help once cyber has approved the request.

S3 data migration can be enabled by adding the `data_migration` parameter along with the `import` parameter and its mandatory configuration to the S3 extension in your `platform-config.yml` file. The `source_kms_key_arn` is optional as it depends on whether the source bucket has KMS key encryption on it.

```yaml
extensions:
  my-s3-bucket:
      type: s3
      services:
        - web
      environments:
        "*":
          bucket_name: bucket_name: my-bucket-dev # Mandatory
          data_migration: # Optional
              import: # Mandatory if data_migration is present
                  source_kms_key_arn: arn:aws:kms::123456789:my-source-key # Optional
                  source_bucket_arn: arn:aws:s3::123456789:my-source-bucket # Mandatory if data_migration is present
                  worker_role_arn: arn:aws:iam::123456789:my-migration-worker-arn # Mandatory if data_migration is present
```

## Using our `demodjango` application for testing

See [instructions in the demodjango-deploy repository](https://github.com/uktrade/demodjango-deploy/tree/main#deploying-a-new-environment).
