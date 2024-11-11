#!/usr/bin/env python
from os import makedirs
from pathlib import Path
from shutil import rmtree

import click

from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.utils.application import get_application_name
from dbt_platform_helper.utils.aws import get_account_details
from dbt_platform_helper.utils.aws import get_codestar_connection_arn
from dbt_platform_helper.utils.aws import get_public_repository_arn
from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.files import generate_override_files_from_template
from dbt_platform_helper.utils.files import mkfile
from dbt_platform_helper.utils.git import git_remote
from dbt_platform_helper.utils.messages import abort_with_error
from dbt_platform_helper.utils.template import setup_templates
from dbt_platform_helper.utils.validation import load_and_validate_platform_config
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)

CODEBASE_PIPELINES_KEY = "codebase_pipelines"
ENVIRONMENTS_KEY = "environments"
ENVIRONMENT_PIPELINES_KEY = "environment_pipelines"


@click.group(chain=True, cls=ClickDocOptGroup)
def pipeline():
    """Pipeline commands."""
    check_platform_helper_version_needs_update()


@pipeline.command()
@click.option(
    "--terraform-platform-modules-version",
    help=f"""Override the default version of terraform-platform-modules with a specific version or branch. 
    Precedence of version used is version supplied via CLI, then the version found in 
    platform-config.yml/default_versions/terraform-platform-modules. 
    In absence of these inputs, defaults to version '{DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION}'.""",
)
@click.option(
    "--deploy-branch",
    help="""Specify the branch of <application>-deploy used to configure the source stage in the environment-pipeline resource. 
    This is generated from the terraform/environments-pipeline/<aws_account>/main.tf file. 
    (Default <application>-deploy branch is specified in 
    <application>-deploy/platform-config.yml/environment_pipelines/<environment-pipeline>/branch).""",
    default=None,
)
def generate(terraform_platform_modules_version, deploy_branch):
    """
    Given a platform-config.yml file, generate environment and service
    deployment pipelines.

    This command does the following in relation to the environment pipelines:
    - Reads contents of `platform-config.yml/environment-pipelines` configuration.
      The `terraform/environment-pipelines/<aws_account>/main.tf` file is generated using this configuration.
      The `main.tf` file is then used to generate Terraform for creating an environment pipeline resource.

    This command does the following in relation to the codebase pipelines:
    - Generates the copilot pipeline manifest.yml for copilot/pipelines/<codebase_pipeline_name>

    (Deprecated) This command does the following for non terraform projects (legacy AWS Copilot):
    - Generates the copilot manifest.yml for copilot/environments/<environment>
    """
    pipeline_config = load_and_validate_platform_config()

    has_codebase_pipelines = CODEBASE_PIPELINES_KEY in pipeline_config
    has_legacy_environment_pipelines = ENVIRONMENTS_KEY in pipeline_config
    has_environment_pipelines = ENVIRONMENT_PIPELINES_KEY in pipeline_config

    if (
        not has_codebase_pipelines
        and not has_legacy_environment_pipelines
        and not has_environment_pipelines
    ):
        click.secho("No pipelines defined: nothing to do.", err=True, fg="yellow")
        return

    platform_config_terraform_modules_default_version = pipeline_config.get(
        "default_versions", {}
    ).get("terraform-platform-modules", "")

    templates = setup_templates()
    app_name = get_application_name()

    git_repo = git_remote()
    if not git_repo:
        abort_with_error("The current directory is not a git repository")

    codestar_connection_arn = get_codestar_connection_arn(app_name)
    if codestar_connection_arn is None:
        abort_with_error(f'There is no CodeStar Connection named "{app_name}" to use')

    base_path = Path(".")
    copilot_pipelines_dir = base_path / f"copilot/pipelines"

    _clean_pipeline_config(copilot_pipelines_dir)

    if has_environment_pipelines:
        environment_pipelines = pipeline_config[ENVIRONMENT_PIPELINES_KEY]

        for config in environment_pipelines.values():
            aws_account = config.get("account")
            _generate_terraform_environment_pipeline_manifest(
                pipeline_config["application"],
                aws_account,
                terraform_platform_modules_version,
                platform_config_terraform_modules_default_version,
                deploy_branch,
            )

    if has_codebase_pipelines:
        account_id, _ = get_account_details()

        for codebase in pipeline_config[CODEBASE_PIPELINES_KEY]:
            _generate_codebase_pipeline(
                account_id,
                app_name,
                codestar_connection_arn,
                git_repo,
                codebase,
                base_path,
                copilot_pipelines_dir,
                templates,
            )


def _clean_pipeline_config(pipelines_dir):
    if pipelines_dir.exists():
        click.echo("Deleting copilot/pipelines directory.")
        rmtree(pipelines_dir)


def _generate_codebase_pipeline(
    account_id,
    app_name,
    codestar_connection_arn,
    git_repo,
    codebase,
    base_path,
    pipelines_dir,
    templates,
):
    makedirs(pipelines_dir / codebase["name"] / "overrides", exist_ok=True)
    environments = []
    for pipelines in codebase["pipelines"]:
        environments += pipelines[ENVIRONMENTS_KEY]

    additional_ecr = codebase.get("additional_ecr_repository", None)
    add_public_perms = additional_ecr and additional_ecr.startswith("public.ecr.aws")
    additional_ecr_arn = get_public_repository_arn(additional_ecr) if add_public_perms else None

    template_data = {
        "account_id": account_id,
        "app_name": app_name,
        "deploy_repo": git_repo,
        "codebase": codebase,
        ENVIRONMENTS_KEY: environments,
        "codestar_connection_arn": codestar_connection_arn,
        "codestar_connection_id": codestar_connection_arn.split("/")[-1],
        "additional_ecr_arn": additional_ecr_arn,
    }

    _create_file_from_template(
        base_path,
        f"{codebase['name']}/manifest.yml",
        pipelines_dir,
        template_data,
        templates,
        "codebase/manifest.yml",
    )

    overrides_path = Path(__file__).parent.parent.joinpath("templates/pipelines/codebase/overrides")
    generate_override_files_from_template(
        base_path, overrides_path, pipelines_dir / codebase["name"] / "overrides", template_data
    )


def _generate_copilot_environments_pipeline(
    app_name, codestar_connection_arn, git_repo, configuration, base_path, pipelines_dir, templates
):
    makedirs(pipelines_dir / "environments/overrides", exist_ok=True)

    template_data = {
        "app_name": app_name,
        "git_repo": git_repo,
        "codestar_connection_arn": codestar_connection_arn,
        "pipeline_environments": configuration,
    }

    _create_file_from_template(
        base_path, "environments/buildspec.yml", pipelines_dir, template_data, templates
    )
    _create_file_from_template(
        base_path, "environments/manifest.yml", pipelines_dir, template_data, templates
    )
    _create_file_from_template(
        base_path, "environments/overrides/cfn.patches.yml", pipelines_dir, template_data, templates
    )


def _create_file_from_template(
    base_path, file_name, pipelines_dir, template_data, templates, template_name=None
):
    contents = templates.get_template(
        f"pipelines/{file_name if template_name is None else template_name}"
    ).render(template_data)
    message = mkfile(base_path, pipelines_dir / file_name, contents, overwrite=True)
    click.echo(message)


def _generate_terraform_environment_pipeline_manifest(
    application,
    aws_account,
    cli_terraform_platform_modules_version,
    platform_config_terraform_modules_default_version,
    deploy_branch,
):
    env_pipeline_template = setup_templates().get_template("environment-pipelines/main.tf")

    terraform_platform_modules_version = _determine_terraform_platform_modules_version(
        cli_terraform_platform_modules_version, platform_config_terraform_modules_default_version
    )

    contents = env_pipeline_template.render(
        {
            "application": application,
            "aws_account": aws_account,
            "terraform_platform_modules_version": terraform_platform_modules_version,
            "deploy_branch": deploy_branch,
        }
    )

    dir_path = f"terraform/environment-pipelines/{aws_account}"
    makedirs(dir_path, exist_ok=True)

    click.echo(mkfile(".", f"{dir_path}/main.tf", contents, overwrite=True))


def _determine_terraform_platform_modules_version(
    cli_terraform_platform_modules_version, platform_config_terraform_modules_default_version
):

    version_preference_order = [
        cli_terraform_platform_modules_version,
        platform_config_terraform_modules_default_version,
        DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION,
    ]
    return [version for version in version_preference_order if version][0]
