#!/usr/bin/env python
from os import makedirs
from pathlib import Path

import click
from yaml.parser import ParserError

from dbt_copilot_helper.utils.application import get_application_name
from dbt_copilot_helper.utils.aws import get_codestar_connection_arn
from dbt_copilot_helper.utils.click import ClickDocOptGroup
from dbt_copilot_helper.utils.files import load_and_validate_config
from dbt_copilot_helper.utils.files import mkfile
from dbt_copilot_helper.utils.git import git_remote
from dbt_copilot_helper.utils.messages import abort_with_error
from dbt_copilot_helper.utils.template import setup_templates
from dbt_copilot_helper.utils.validation import PIPELINES_SCHEMA
from dbt_copilot_helper.utils.versioning import (
    check_copilot_helper_version_needs_update,
)


@click.group(chain=True, cls=ClickDocOptGroup)
def pipeline():
    """Pipeline commands."""
    check_copilot_helper_version_needs_update()


@pipeline.command()
def generate():
    """Given a pipelines.yml file, generate environment and service deployment
    pipelines."""
    templates = setup_templates()

    app_name = get_application_name()

    pipeline_config = _safe_load_config("pipelines.yml", PIPELINES_SCHEMA)

    _validate_pipelines_configuration(pipeline_config)

    git_repo = git_remote()
    if not git_repo:
        abort_with_error("The current directory is not a git repository")

    codestar_connection_arn = get_codestar_connection_arn(app_name)
    if codestar_connection_arn is None:
        abort_with_error("There is no CodeStar Connection to use")

    if "environments" in pipeline_config:
        _generate_environments_pipeline(
            app_name, codestar_connection_arn, git_repo, pipeline_config["environments"], templates
        )

    if "codebases" in pipeline_config:
        for codebase in pipeline_config["codebases"]:
            _generate_codebase_pipeline(
                app_name, codestar_connection_arn, git_repo, codebase, templates
            )


def _validate_pipelines_configuration(pipeline_config):
    if not ("codebases" in pipeline_config or "environments" in pipeline_config):
        abort_with_error("No environment or codebase pipelines defined in pipelines.yml")

    if "codebases" in pipeline_config:
        for codebase in pipeline_config["codebases"]:
            codebase_environments = []

            for pipeline in codebase["pipelines"]:
                codebase_environments += [e["name"] for e in pipeline["environments"]]

            unique_codebase_environments = sorted(list(set(codebase_environments)))

            if sorted(codebase_environments) != sorted(unique_codebase_environments):
                abort_with_error(
                    "The pipelines.yml file is invalid, each environment can only be "
                    "listed in a single pipeline per codebase"
                )


def _generate_codebase_pipeline(app_name, codestar_connection_arn, git_repo, codebase, templates):
    base_path = Path(".")
    pipelines_dir = base_path / f"copilot/pipelines"
    makedirs(pipelines_dir / codebase["name"] / "overrides", exist_ok=True)

    environments = []
    for pipelines in codebase["pipelines"]:
        environments += pipelines["environments"]

    template_data = {
        "app_name": app_name,
        "deploy_repo": git_repo,
        "codebase": codebase,
        "environments": environments,
        "codestar_connection_arn": codestar_connection_arn,
        "codestar_connection_id": codestar_connection_arn.split("/")[-1],
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

    for file in overrides_path.glob("*"):
        if file.is_file():
            contents = file.read_text()
            file_name = str(file).removeprefix(f"{overrides_path}/")
            click.echo(
                mkfile(
                    base_path,
                    pipelines_dir / codebase["name"] / "overrides" / file_name,
                    contents,
                    overwrite=True,
                )
            )

    for file in overrides_path.glob("bin/*"):
        if file.is_file():
            contents = file.read_text()
            file_name = str(file).removeprefix(f"{overrides_path}/")
            click.echo(
                mkfile(
                    base_path,
                    pipelines_dir / codebase["name"] / "overrides" / file_name,
                    contents,
                    overwrite=True,
                )
            )


def _generate_environments_pipeline(
    app_name, codestar_connection_arn, git_repo, configuration, templates
):
    base_path = Path(".")
    pipelines_dir = base_path / f"copilot/pipelines"
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
    click.echo(mkfile(base_path, pipelines_dir / file_name, contents, overwrite=True))


def _safe_load_config(filename, schema):
    try:
        return load_and_validate_config(filename, schema)
    except FileNotFoundError:
        abort_with_error(f"There is no {filename}")
    except ParserError:
        abort_with_error(f"The {filename} file is invalid")
