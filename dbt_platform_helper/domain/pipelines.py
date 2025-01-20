from collections.abc import Callable
from os import makedirs
from pathlib import Path
from shutil import rmtree

from dbt_platform_helper.constants import CODEBASE_PIPELINES_KEY
from dbt_platform_helper.constants import ENVIRONMENT_PIPELINES_KEY
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.providers.terraform_manifest import TerraformManifestProvider
from dbt_platform_helper.utils.application import get_application_name
from dbt_platform_helper.utils.template import setup_templates
from dbt_platform_helper.utils.versioning import (
    get_required_terraform_platform_modules_version,
)


class Pipelines:
    def __init__(
        self,
        config_provider: ConfigProvider,
        terraform_manifest_provider: TerraformManifestProvider,
        echo: Callable[[str], str],
        abort: Callable[[str], None],
        get_git_remote: Callable[[], str],
        get_codestar_arn: Callable[[str], str],
    ):
        self.config_provider = config_provider
        self.echo = echo
        self.abort = abort
        self.get_git_remote = get_git_remote
        self.get_codestar_arn = get_codestar_arn
        self.terraform_manifest_provider = terraform_manifest_provider

    def generate(self, terraform_platform_modules_version, deploy_branch):
        platform_config = self.config_provider.load_and_validate_platform_config()

        has_codebase_pipelines = CODEBASE_PIPELINES_KEY in platform_config
        has_environment_pipelines = ENVIRONMENT_PIPELINES_KEY in platform_config

        if not (has_codebase_pipelines or has_environment_pipelines):
            self.echo("No pipelines defined: nothing to do.", err=True, fg="yellow")
            return

        platform_config_terraform_modules_default_version = platform_config.get(
            "default_versions", {}
        ).get("terraform-platform-modules", "")

        app_name = get_application_name()

        git_repo = self.get_git_remote()
        if not git_repo:
            self.abort("The current directory is not a git repository")

        codestar_connection_arn = self.get_codestar_arn(app_name)
        if codestar_connection_arn is None:
            self.abort(f'There is no CodeStar Connection named "{app_name}" to use')

        base_path = Path(".")
        copilot_pipelines_dir = base_path / f"copilot/pipelines"

        self._clean_pipeline_config(copilot_pipelines_dir)

        if has_environment_pipelines:
            environment_pipelines = platform_config[ENVIRONMENT_PIPELINES_KEY]

            for config in environment_pipelines.values():
                aws_account = config.get("account")
                self._generate_terraform_environment_pipeline_manifest(
                    platform_config["application"],
                    aws_account,
                    terraform_platform_modules_version,
                    platform_config_terraform_modules_default_version,
                    deploy_branch,
                )

        if has_codebase_pipelines:
            self.terraform_manifest_provider.generate_codebase_pipeline_config(platform_config)

    def _clean_pipeline_config(self, pipelines_dir):
        if pipelines_dir.exists():
            self.echo("Deleting copilot/pipelines directory.")
            rmtree(pipelines_dir)

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

        self.echo(FileProvider.mkfile(".", f"{dir_path}/main.tf", contents, overwrite=True))
