from collections.abc import Callable
from os import makedirs
from pathlib import Path
from shutil import rmtree

from dbtp_inspector.constants import PLATFORM_CONFIG_FILE

from dbt_platform_helper.constants import CODEBASE_PIPELINES_KEY
from dbt_platform_helper.constants import ENVIRONMENT_PIPELINES_KEY
from dbt_platform_helper.constants import SUPPORTED_AWS_PROVIDER_VERSION
from dbt_platform_helper.constants import SUPPORTED_TERRAFORM_VERSION
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.ecr import ECRProvider
from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.terraform_manifest import TerraformManifestProvider
from dbt_platform_helper.utils.git import git_remote
from dbt_platform_helper.utils.template import setup_templates


class Pipelines:
    def __init__(
        self,
        config_provider: ConfigProvider,
        terraform_manifest_provider: TerraformManifestProvider = TerraformManifestProvider(),
        ecr_provider: ECRProvider = ECRProvider(),
        get_git_remote: Callable[[], str] = git_remote,
        io: ClickIOProvider = ClickIOProvider(),
        file_provider: FileProvider = FileProvider(),
        platform_helper_versioning: PlatformHelperVersioning = None,
    ):
        self.config_provider = config_provider
        self.get_git_remote = get_git_remote
        self.terraform_manifest_provider = terraform_manifest_provider
        self.ecr_provider = ecr_provider
        self.io = io
        self.file_provider = file_provider
        self.platform_helper_versioning = platform_helper_versioning

    def _map_environment_pipeline_accounts(self, platform_config) -> list[tuple[str, str]]:
        environment_pipelines_config = platform_config[ENVIRONMENT_PIPELINES_KEY]
        environment_config = platform_config["environments"]

        account_id_lookup = {
            env["accounts"]["deploy"]["name"]: env["accounts"]["deploy"]["id"]
            for env in environment_config.values()
            if env is not None and "accounts" in env and "deploy" in env["accounts"]
        }

        accounts = set()

        for config in environment_pipelines_config.values():
            account = config.get("account")
            deploy_account_id = account_id_lookup.get(account)
            accounts.add((account, deploy_account_id))

        return list(accounts)

    def generate(self, deploy_branch: str, workspace: str = None):
        self.platform_helper_versioning.check_platform_helper_version_mismatch()

        platform_config_file_name = (
            f"platform-config.{workspace}.yml" if workspace else PLATFORM_CONFIG_FILE
        )
        platform_config = self.config_provider.load_and_validate_platform_config(
            path=platform_config_file_name
        )

        has_codebase_pipelines = CODEBASE_PIPELINES_KEY in platform_config
        has_environment_pipelines = ENVIRONMENT_PIPELINES_KEY in platform_config

        if not (has_codebase_pipelines or has_environment_pipelines):
            self.io.warn("No pipelines defined: nothing to do.")
            return

        git_repo = self.get_git_remote()
        if not git_repo:
            self.io.abort_with_error("The current directory is not a git repository")

        base_path = Path(".")
        copilot_pipelines_dir = base_path / f"copilot/pipelines"

        self._clean_pipeline_config(copilot_pipelines_dir)

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
            accounts = self._map_environment_pipeline_accounts(platform_config)

            for account_name, account_id in accounts:
                self._generate_terraform_environment_pipeline_manifest(
                    platform_config["application"],
                    deploy_repository,
                    account_name,
                    self.platform_helper_versioning.get_environment_pipeline_modules_source(),
                    deploy_branch,
                    account_id,
                    self.platform_helper_versioning.get_pinned_version(),
                    workspace,
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
                self.platform_helper_versioning.get_template_version(),
                ecrs_that_need_importing,
                deploy_repository,
                self.platform_helper_versioning.get_codebase_pipeline_modules_source(),
                workspace,
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
        module_source: str,
        deploy_branch: str,
        aws_account_id: str,
        pinned_version: str,
        workspace: str = None,
    ):
        env_pipeline_template = setup_templates().get_template("environment-pipelines/main.tf")

        platform_config_file_name = (
            f"platform-config.{workspace}.yml" if workspace else PLATFORM_CONFIG_FILE
        )
        contents = env_pipeline_template.render(
            {
                "application": application,
                "deploy_repository": deploy_repository,
                "aws_account": aws_account,
                "module_source": module_source,
                "deploy_branch": deploy_branch,
                "terraform_version": SUPPORTED_TERRAFORM_VERSION,
                "aws_provider_version": SUPPORTED_AWS_PROVIDER_VERSION,
                "deploy_account_id": aws_account_id,
                "pinned_version": pinned_version,
                "platform_config_file_name": platform_config_file_name,
            }
        )

        dir_path = f"terraform/environment-pipelines/{aws_account}"
        makedirs(dir_path, exist_ok=True)

        self.io.info(
            self.file_provider.mkfile(".", f"{dir_path}/main.tf", contents, overwrite=True)
        )
