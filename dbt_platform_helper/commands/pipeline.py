#!/usr/bin/env python
import click

from dbt_platform_helper.domain.pipelines import Pipelines
from dbt_platform_helper.domain.pipelines import PipelineVersioning
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.ecr import ECRProvider
from dbt_platform_helper.providers.environment_variable import (
    EnvironmentVariableProvider,
)
from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.terraform_manifest import TerraformManifestProvider
from dbt_platform_helper.utils.aws import get_codestar_connection_arn
from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.git import git_remote


@click.group(chain=True, cls=ClickDocOptGroup)
def pipeline():
    """Pipeline commands."""
    PlatformHelperVersioning().check_if_needs_update()


@pipeline.command()
@click.option(
    "--deploy-branch",
    help="""Specify the branch of <application>-deploy used to configure the source stage in the environment-pipeline resource. 
    This is generated from the terraform/environments-pipeline/<aws_account>/main.tf file. 
    (Default <application>-deploy branch is specified in 
    <application>-deploy/platform-config.yml/environment_pipelines/<environment-pipeline>/branch).""",
    default=None,
)
def generate(deploy_branch: str):
    """
    Given a platform-config.yml file, generate environment and service
    deployment pipelines.

    This command does the following in relation to the environment pipelines:
    - Reads contents of `platform-config.yml/environment_pipelines` configuration.
      The `terraform/environment-pipelines/<aws_account>/main.tf` file is generated using this configuration.
      The `main.tf` file is then used to generate Terraform for creating an environment pipeline resource.

    This command does the following in relation to the codebase pipelines:
    - Reads contents of `platform-config.yml/codebase_pipelines` configuration.
      The `terraform/codebase-pipelines/main.tf.json` file is generated using this configuration.
      The `main.tf.json` file is then used to generate Terraform for creating a codebase pipeline resource.
    """
    config_provider = ConfigProvider(ConfigValidator())
    environment_variable_provider = EnvironmentVariableProvider()
    pipeline_versioning = PipelineVersioning(
        config_provider,
        environment_variable_provider,
        None,
    )
    io = ClickIOProvider()

    try:
        pipelines = Pipelines(
            config_provider,
            TerraformManifestProvider(),
            ECRProvider(),
            git_remote,
            get_codestar_connection_arn,
            io,
            FileProvider(),
            pipeline_versioning,
        )
        pipelines.generate(deploy_branch)
    except Exception as exc:
        io.abort_with_error(str(exc))
