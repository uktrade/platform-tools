import os
from collections.abc import Callable
from os import makedirs
from pathlib import Path
from shutil import rmtree

from dbt_platform_helper.constants import CODEBASE_PIPELINES_KEY
from dbt_platform_helper.constants import ENVIRONMENT_PIPELINES_KEY
from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_OVERRIDE_KEY
from dbt_platform_helper.constants import SUPPORTED_AWS_PROVIDER_VERSION
from dbt_platform_helper.constants import SUPPORTED_TERRAFORM_VERSION
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.ecr import ECRProvider
from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.terraform_manifest import TerraformManifestProvider
from dbt_platform_helper.utils.application import get_application_name
from dbt_platform_helper.utils.template import setup_templates


class Pipelines:
    def __init__(
        self,
        config_provider: ConfigProvider,
        terraform_manifest_provider: TerraformManifestProvider,
        ecr_provider: ECRProvider,
        get_git_remote: Callable[[], str],
        get_codestar_arn: Callable[[str], str],
        io: ClickIOProvider = ClickIOProvider(),
        file_provider: FileProvider = FileProvider(),
        platform_helper_version_override: str = None,
    ):
        self.config_provider = config_provider
        self.get_git_remote = get_git_remote
        self.get_codestar_arn = get_codestar_arn
        self.terraform_manifest_provider = terraform_manifest_provider
        self.ecr_provider = ecr_provider
        self.io = io
        self.file_provider = file_provider
        self.platform_helper_version_override = platform_helper_version_override or os.environ.get(
            PLATFORM_HELPER_VERSION_OVERRIDE_KEY
        )

    def generate(
        self,
        deploy_branch: str,
    ):
        platform_config = self.config_provider.load_and_validate_platform_config()

        has_codebase_pipelines = CODEBASE_PIPELINES_KEY in platform_config
        has_environment_pipelines = ENVIRONMENT_PIPELINES_KEY in platform_config

        if not (has_codebase_pipelines or has_environment_pipelines):
            self.io.warn("No pipelines defined: nothing to do.")
            return

        app_name = get_application_name()

        git_repo = self.get_git_remote()
        if not git_repo:
            self.io.abort_with_error("The current directory is not a git repository")

        codestar_connection_arn = self.get_codestar_arn(app_name)
        if codestar_connection_arn is None:
            self.io.abort_with_error(f'There is no CodeStar Connection named "{app_name}" to use')

        base_path = Path(".")
        copilot_pipelines_dir = base_path / f"copilot/pipelines"

        self._clean_pipeline_config(copilot_pipelines_dir)

        platform_helper_version_for_template: str = platform_config.get("default_versions", {}).get(
            "platform-helper"
        )

        if self.platform_helper_version_override:
            platform_helper_version_for_template = self.platform_helper_version_override

        # TODO: DBTP-1965: - this whole code block/if-statement can fall away once the deploy_repository is a required key.
        deploy_repository = ""
        if "deploy_repository" in platform_config.keys():
            deploy_repository = f"{platform_config['deploy_repository']}"
        else:
            self.io.warn(
                "No `deploy_repository` key set in platform-config.yml, this will become a required key. See full platform config reference in the docs: https://platform.readme.trade.gov.uk/reference/platform-config-yml/#core-configuration"
            )
            deploy_repository = f"uktrade/{platform_config['application']}-deploy"

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
                    deploy_repository,
                    account,
                    platform_helper_version_for_template,
                    deploy_branch,
                )

        if has_codebase_pipelines:
            codebase_pipelines = platform_config[CODEBASE_PIPELINES_KEY]
            ecrs_to_be_managed = {
                codebase: f"{platform_config['application']}/{codebase}"
                for codebase in codebase_pipelines.keys()
            }
            ecrs_already_provisioned = set(self.ecr_provider.get_ecr_repo_names())
            ecrs_that_need_importing = {
                codebase: repo
                for codebase, repo in ecrs_to_be_managed.items()
                if repo in ecrs_already_provisioned
            }

            self.terraform_manifest_provider.generate_codebase_pipeline_config(
                platform_config,
                platform_helper_version_for_template,
                ecrs_that_need_importing,
                deploy_repository,
            )

    def _clean_pipeline_config(self, pipelines_dir: Path):
        if pipelines_dir.exists():
            self.io.info("Deleting copilot/pipelines directory.")
            rmtree(pipelines_dir)

    def _generate_terraform_environment_pipeline_manifest(
        self,
        application: str,
        deploy_repository: str,
        aws_account: str,
        platform_helper_version: str,
        deploy_branch: str,
    ):
        env_pipeline_template = setup_templates().get_template("environment-pipelines/main.tf")

        contents = env_pipeline_template.render(
            {
                "application": application,
                "deploy_repository": deploy_repository,
                "aws_account": aws_account,
                "platform_helper_version": platform_helper_version,
                "deploy_branch": deploy_branch,
                "terraform_version": SUPPORTED_TERRAFORM_VERSION,
                "aws_provider_version": SUPPORTED_AWS_PROVIDER_VERSION,
            }
        )

        dir_path = f"terraform/environment-pipelines/{aws_account}"
        makedirs(dir_path, exist_ok=True)

        self.io.info(
            self.file_provider.mkfile(".", f"{dir_path}/main.tf", contents, overwrite=True)
        )
