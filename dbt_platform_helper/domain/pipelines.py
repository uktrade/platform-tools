from collections.abc import Callable
from os import makedirs
from pathlib import Path
from shutil import rmtree

import click

from dbt_platform_helper.constants import CODEBASE_PIPELINES_KEY
from dbt_platform_helper.constants import ENVIRONMENT_PIPELINES_KEY
from dbt_platform_helper.constants import ENVIRONMENTS_KEY
from dbt_platform_helper.domain.config_validator import ConfigValidator
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.utils.application import get_application_name
from dbt_platform_helper.utils.aws import get_account_details
from dbt_platform_helper.utils.aws import get_codestar_connection_arn
from dbt_platform_helper.utils.aws import get_public_repository_arn
from dbt_platform_helper.utils.files import generate_override_files_from_template
from dbt_platform_helper.utils.files import mkfile
from dbt_platform_helper.utils.git import git_remote
from dbt_platform_helper.utils.messages import abort_with_error
from dbt_platform_helper.utils.template import setup_templates
from dbt_platform_helper.utils.versioning import (
    get_required_terraform_platform_modules_version,
)


class Pipelines:
    def __init__(
        self,
        config_provider=ConfigProvider(ConfigValidator()),
        echo: Callable[[str], str] = click.secho,
        abort: Callable[[str], None] = abort_with_error,
    ):
        self.config_provider = config_provider
        self.echo = echo
        self.abort = abort

    def generate(self, terraform_platform_modules_version, deploy_branch):
        pipeline_config = self.config_provider.load_and_validate_platform_config()

        has_codebase_pipelines = CODEBASE_PIPELINES_KEY in pipeline_config
        has_environment_pipelines = ENVIRONMENT_PIPELINES_KEY in pipeline_config

        if not (has_codebase_pipelines or has_environment_pipelines):
            self.echo("No pipelines defined: nothing to do.", err=True, fg="yellow")
            return

        platform_config_terraform_modules_default_version = pipeline_config.get(
            "default_versions", {}
        ).get("terraform-platform-modules", "")

        templates = setup_templates()
        app_name = get_application_name()

        git_repo = git_remote()
        if not git_repo:
            self.abort("The current directory is not a git repository")

        codestar_connection_arn = get_codestar_connection_arn(app_name)
        if codestar_connection_arn is None:
            self.abort(f'There is no CodeStar Connection named "{app_name}" to use')

        base_path = Path(".")
        copilot_pipelines_dir = base_path / f"copilot/pipelines"

        self._clean_pipeline_config(copilot_pipelines_dir)

        if has_environment_pipelines:
            environment_pipelines = pipeline_config[ENVIRONMENT_PIPELINES_KEY]

            for config in environment_pipelines.values():
                aws_account = config.get("account")
                self._generate_terraform_environment_pipeline_manifest(
                    pipeline_config["application"],
                    aws_account,
                    terraform_platform_modules_version,
                    platform_config_terraform_modules_default_version,
                    deploy_branch,
                )

        if has_codebase_pipelines:
            account_id, _ = get_account_details()

            for codebase in pipeline_config[CODEBASE_PIPELINES_KEY]:
                self._generate_codebase_pipeline(
                    account_id,
                    app_name,
                    codestar_connection_arn,
                    git_repo,
                    codebase,
                    base_path,
                    copilot_pipelines_dir,
                    templates,
                )

    def _clean_pipeline_config(self, pipelines_dir):
        if pipelines_dir.exists():
            click.echo("Deleting copilot/pipelines directory.")
            rmtree(pipelines_dir)

    def _generate_codebase_pipeline(
        self,
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

        self._create_file_from_template(
            base_path,
            f"{codebase['name']}/manifest.yml",
            pipelines_dir,
            template_data,
            templates,
            "codebase/manifest.yml",
        )

        overrides_path = Path(__file__).parent.parent.joinpath(
            "templates/pipelines/codebase/overrides"
        )
        generate_override_files_from_template(
            base_path, overrides_path, pipelines_dir / codebase["name"] / "overrides", template_data
        )

    def _create_file_from_template(
        self, base_path, file_name, pipelines_dir, template_data, templates, template_name=None
    ):
        contents = templates.get_template(
            f"pipelines/{file_name if template_name is None else template_name}"
        ).render(template_data)
        message = mkfile(base_path, pipelines_dir / file_name, contents, overwrite=True)
        click.echo(message)

    def _generate_terraform_environment_pipeline_manifest(
        self,
        application,
        aws_account,
        cli_terraform_platform_modules_version,
        platform_config_terraform_modules_default_version,
        deploy_branch,
    ):
        env_pipeline_template = setup_templates().get_template("environment-pipelines/main.tf")

        terraform_platform_modules_version = get_required_terraform_platform_modules_version(
            cli_terraform_platform_modules_version,
            platform_config_terraform_modules_default_version,
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
