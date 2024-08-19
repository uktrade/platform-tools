#!/usr/bin/env python
from os import makedirs
from pathlib import Path
from shutil import rmtree

import click

from dbt_platform_helper.utils.application import get_application_name
from dbt_platform_helper.utils.aws import get_account_details
from dbt_platform_helper.utils.aws import get_codestar_connection_arn
from dbt_platform_helper.utils.aws import get_public_repository_arn
from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.files import apply_environment_defaults
from dbt_platform_helper.utils.files import generate_override_files_from_template
from dbt_platform_helper.utils.files import mkfile
from dbt_platform_helper.utils.git import git_remote
from dbt_platform_helper.utils.messages import abort_with_error
from dbt_platform_helper.utils.platform_config import is_terraform_project
from dbt_platform_helper.utils.template import setup_templates
from dbt_platform_helper.utils.validation import load_and_validate_platform_config
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)

CODEBASE_PIPELINES_KEY = "codebase_pipelines"
ENVIRONMENTS_KEY = "environments"


@click.group(chain=True, cls=ClickDocOptGroup)
def pipeline():
    """Pipeline commands."""
    check_platform_helper_version_needs_update()


@pipeline.command()
def generate():
    """Given a platform-config.yml file, generate environment and service
    deployment pipelines."""
    pipeline_config = load_and_validate_platform_config()

    no_codebase_pipelines = CODEBASE_PIPELINES_KEY not in pipeline_config
    no_environment_pipelines = ENVIRONMENTS_KEY not in pipeline_config

    if no_codebase_pipelines and no_environment_pipelines:
        click.secho("No pipelines defined: nothing to do.", err=True, fg="yellow")
        return

    templates = setup_templates()
    app_name = get_application_name()

    git_repo = git_remote()
    if not git_repo:
        abort_with_error("The current directory is not a git repository")

    codestar_connection_arn = get_codestar_connection_arn(app_name)
    if codestar_connection_arn is None:
        abort_with_error(f'There is no CodeStar Connection named "{app_name}" to use')

    base_path = Path(".")
    pipelines_dir = base_path / f"copilot/pipelines"

    _clean_pipeline_config(pipelines_dir)

    if not is_terraform_project() and ENVIRONMENTS_KEY in pipeline_config:
        _generate_copilot_environments_pipeline(
            app_name,
            codestar_connection_arn,
            git_repo,
            apply_environment_defaults(pipeline_config)[ENVIRONMENTS_KEY],
            base_path,
            pipelines_dir,
            templates,
        )

    if CODEBASE_PIPELINES_KEY in pipeline_config:
        account_id, _ = get_account_details()

        for codebase in pipeline_config[CODEBASE_PIPELINES_KEY]:
            _generate_codebase_pipeline(
                account_id,
                app_name,
                codestar_connection_arn,
                git_repo,
                codebase,
                base_path,
                pipelines_dir,
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
