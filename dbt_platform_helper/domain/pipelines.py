from collections.abc import Callable
from os import makedirs
from pathlib import Path
from shutil import rmtree

from dbt_platform_helper.constants import CODEBASE_PIPELINES_KEY
from dbt_platform_helper.constants import ENVIRONMENT_PIPELINES_KEY
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.ecr import ECRProvider
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
        ecr_provider: ECRProvider,
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
        self.ecr_provider = ecr_provider

    def generate(self, cli_terraform_platform_modules_version, deploy_branch):
        try:
            self._generate_pipeline_config(cli_terraform_platform_modules_version, deploy_branch)
        except Exception as exc:
            self.abort(str(exc))

    def _generate_pipeline_config(self, cli_terraform_platform_modules_version, deploy_branch):
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

        terraform_platform_modules_version = get_required_terraform_platform_modules_version(
            cli_terraform_platform_modules_version,
            platform_config_terraform_modules_default_version,
        )

        if has_environment_pipelines:
            environment_pipelines = platform_config[ENVIRONMENT_PIPELINES_KEY]
            accounts = {
                config.get("account")
                for config in environment_pipelines.values()
                if "account" in config
            }

            for account in accounts:
                self._generate_terraform_environment_pipeline_manifest(
                    platform_config["application"],
                    account,
                    terraform_platform_modules_version,
                    deploy_branch,
                )

        if has_codebase_pipelines:
            codebase_pipelines = platform_config[CODEBASE_PIPELINES_KEY]
            provisioned_ecrs = set(self.ecr_provider.get_ecr_repo_names())
            required_ecrs = {
                codebase: f"{platform_config['application']}/{codebase}"
                for codebase in codebase_pipelines.keys()
                if f"{platform_config['application']}/{codebase}" in provisioned_ecrs
            }
            required_imports = {
                codebase: repo
                for codebase, repo in required_ecrs.items()
                if repo in provisioned_ecrs
            }

            self.terraform_manifest_provider.generate_codebase_pipeline_config(
                platform_config, terraform_platform_modules_version, required_imports
            )

    def _clean_pipeline_config(self, pipelines_dir):
        if pipelines_dir.exists():
            self.echo("Deleting copilot/pipelines directory.")
            rmtree(pipelines_dir)

    def _generate_terraform_environment_pipeline_manifest(
        self,
        application,
        aws_account,
        terraform_platform_modules_version,
        deploy_branch,
    ):
        env_pipeline_template = setup_templates().get_template("environment-pipelines/main.tf")

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
