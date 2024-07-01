#!/usr/bin/env python
from os import makedirs
from pathlib import Path
from shutil import rmtree

import click
from yaml.parser import ParserError

from dbt_platform_helper.utils.application import get_application_name
from dbt_platform_helper.utils.aws import get_account_details
from dbt_platform_helper.utils.aws import get_codestar_connection_arn
from dbt_platform_helper.utils.aws import get_public_repository_arn
from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.files import PLATFORM_CONFIG_FILE
from dbt_platform_helper.utils.files import apply_environment_defaults
from dbt_platform_helper.utils.files import config_file_check
from dbt_platform_helper.utils.files import generate_override_files
from dbt_platform_helper.utils.files import is_terraform_project
from dbt_platform_helper.utils.files import load_and_validate_config
from dbt_platform_helper.utils.files import mkfile
from dbt_platform_helper.utils.git import git_remote
from dbt_platform_helper.utils.messages import abort_with_error
from dbt_platform_helper.utils.template import setup_templates
from dbt_platform_helper.utils.validation import PLATFORM_CONFIG_SCHEMA
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
    templates = setup_templates()

    app_name = get_application_name()

    config_file_check()
    pipeline_config = _safe_load_config(PLATFORM_CONFIG_FILE, PLATFORM_CONFIG_SCHEMA)

    _validate_pipelines_configuration(pipeline_config)

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


def _validate_pipelines_configuration(pipeline_config):
    if not (CODEBASE_PIPELINES_KEY in pipeline_config or ENVIRONMENTS_KEY in pipeline_config):
        abort_with_error(f"No environment or codebase pipelines defined in {PLATFORM_CONFIG_FILE}")

    if CODEBASE_PIPELINES_KEY in pipeline_config:
        for codebase in pipeline_config[CODEBASE_PIPELINES_KEY]:
            codebase_environments = []

            for pipeline in codebase["pipelines"]:
                codebase_environments += [e["name"] for e in pipeline[ENVIRONMENTS_KEY]]

            unique_codebase_environments = sorted(list(set(codebase_environments)))

            if sorted(codebase_environments) != sorted(unique_codebase_environments):
                abort_with_error(
                    f"The {PLATFORM_CONFIG_FILE} file is invalid, each environment can only be "
                    "listed in a single pipeline per codebase"
                )


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
    generate_override_files(
        base_path, overrides_path, pipelines_dir / codebase["name"] / "overrides"
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


def _safe_load_config(filename, schema):
    try:
        return load_and_validate_config(filename, schema)
    except ParserError:
        abort_with_error(f"The {filename} file is invalid")
