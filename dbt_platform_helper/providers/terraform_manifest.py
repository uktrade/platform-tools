import json
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

from dbt_platform_helper.constants import SUPPORTED_AWS_PROVIDER_VERSION
from dbt_platform_helper.constants import SUPPORTED_TERRAFORM_VERSION
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.providers.io import ClickIOProvider


class TerraformManifestProvider:
    def __init__(
        self, file_provider: FileProvider = FileProvider(), io: ClickIOProvider = ClickIOProvider()
    ):
        self.file_provider = file_provider
        self.io = io

    def generate_codebase_pipeline_config(
        self,
        platform_config: dict,
        terraform_platform_modules_version: str,
        ecr_imports: dict[str, str],
    ):
        default_account = self._get_account_for_env("*", platform_config)
        state_key_suffix = f"{platform_config['application']}-codebase-pipelines"

        terraform = {}
        self._add_header(terraform)
        self._add_codebase_pipeline_locals(terraform)
        self._add_provider(terraform, default_account)
        self._add_backend(terraform, platform_config, default_account, state_key_suffix)
        self._add_codebase_pipeline_module(terraform, terraform_platform_modules_version)
        self._add_imports(terraform, ecr_imports)
        self._write_terraform_json(terraform, "terraform/codebase-pipelines")

    def generate_environment_config(
        self,
        platform_config: dict,
        env: str,
        terraform_platform_modules_version: str,
    ):
        platform_config = ConfigProvider.apply_environment_defaults(platform_config)
        account = self._get_account_for_env(env, platform_config)

        application_name = platform_config["application"]
        state_key_suffix = f"{platform_config['application']}-{env}"
        env_dir = f"terraform/environments/{env}"

        terraform = {}
        self._add_header(terraform)
        self._add_environment_locals(terraform, application_name)
        self._add_backend(terraform, platform_config, account, state_key_suffix)
        self._add_extensions_module(terraform, terraform_platform_modules_version, env)
        self._add_moved(terraform, platform_config)
        self._ensure_no_hcl_manifest_file(env_dir)
        self._write_terraform_json(terraform, env_dir)

    @staticmethod
    def _get_account_for_env(env, platform_config):
        account = (
            platform_config.get("environments", {})
            .get(env, {})
            .get("accounts", {})
            .get("deploy", {})
            .get("name")
        )
        return account

    @staticmethod
    def _add_header(terraform: dict):
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        version_header = f"Generated by platform-helper {version('dbt-platform-helper')} / {time}."
        warning = "WARNING: This is an autogenerated file, not for manual editing."
        # The "//" key denotes a comment in terraform json.
        terraform["//"] = f"{version_header} {warning}"

    @staticmethod
    def _add_codebase_pipeline_locals(terraform: dict):
        terraform["locals"] = {
            "platform_config": '${yamldecode(file("../../platform-config.yml"))}',
            "application": '${local.platform_config["application"]}',
            "all_codebases": '${local.platform_config["codebase_pipelines"]}',
            "environments": '${local.platform_config["environments"]}',
        }

    @staticmethod
    def _add_provider(terraform: dict, default_account: str):
        terraform["provider"] = {"aws": {}}
        terraform["provider"]["aws"]["region"] = "eu-west-2"
        terraform["provider"]["aws"]["profile"] = default_account
        terraform["provider"]["aws"]["alias"] = default_account
        terraform["provider"]["aws"]["shared_credentials_files"] = ["~/.aws/config"]

    @staticmethod
    def _add_backend(terraform: dict, platform_config: dict, account: str, state_key_suffix: str):
        terraform["terraform"] = {
            "required_version": SUPPORTED_TERRAFORM_VERSION,
            "backend": {
                "s3": {
                    "bucket": f"terraform-platform-state-{account}",
                    "key": f"tfstate/application/{state_key_suffix}.tfstate",
                    "region": "eu-west-2",
                    "encrypt": True,
                    "kms_key_id": f"alias/terraform-platform-state-s3-key-{account}",
                    "dynamodb_table": f"terraform-platform-lockdb-{account}",
                }
            },
            "required_providers": {
                "aws": {"source": "hashicorp/aws", "version": SUPPORTED_AWS_PROVIDER_VERSION}
            },
        }

    @staticmethod
    def _add_codebase_pipeline_module(terraform: dict, terraform_platform_modules_version: str):
        source = f"git::https://github.com/uktrade/terraform-platform-modules.git//codebase-pipelines?depth=1&ref={terraform_platform_modules_version}"
        terraform["module"] = {
            "codebase-pipelines": {
                "source": source,
                "for_each": "${local.all_codebases}",
                "application": "${local.application}",
                "codebase": "${each.key}",
                "repository": "${each.value.repository}",
                "additional_ecr_repository": '${lookup(each.value, "additional_ecr_repository", null)}',
                "pipelines": '${lookup(each.value, "pipelines", [])}',
                "services": "${each.value.services}",
                "requires_image_build": '${lookup(each.value, "requires_image_build", true)}',
                "slack_channel": '${lookup(each.value, "slack_channel", "/codebuild/slack_oauth_channel")}',
                "env_config": "${local.environments}",
            }
        }

    @staticmethod
    def _add_extensions_module(terraform: dict, terraform_platform_modules_version: str, env: str):
        source = f"git::https://github.com/uktrade/terraform-platform-modules.git//extensions?depth=1&ref={terraform_platform_modules_version}"
        terraform["module"] = {
            "extensions": {"source": source, "args": "${local.args}", "environment": env}
        }

    @staticmethod
    def _add_imports(terraform: dict, ecr_imports: dict[str, str]):
        if ecr_imports:
            terraform["import"] = {
                "for_each": "${%s}" % json.dumps(ecr_imports),
                "id": "${each.value}",
                "to": "module.codebase-pipelines[each.key].aws_ecr_repository.this",
            }

    @staticmethod
    def _add_environment_locals(terraform: dict, app: str):
        terraform["locals"] = {
            "config": '${yamldecode(file("../../../platform-config.yml"))}',
            "environments": '${local.config["environments"]}',
            "env_config": '${{for name, config in local.environments: name => merge(lookup(local.environments, "*", {}), config)}}',
            "args": {
                "application": app,
                "services": '${local.config["extensions"]}',
                "env_config": "${local.env_config}",
            },
        }

    @staticmethod
    def _add_moved(terraform, platform_config):
        extensions_comment = "Moved extensions-tf to just extensions - this block tells terraform this. Can be removed once all services have moved to the new naming."
        terraform["moved"] = [
            {
                "//": extensions_comment,
                "from": "module.extensions-tf",
                "to": "module.extensions",
            }
        ]

        extensions = platform_config.get("extensions", {})
        s3_extension_names = [
            extension_name
            for extension_name, extension in extensions.items()
            if extension["type"] == "s3"
        ]
        s3_comment = "S3 bucket resources are now indexed. Can be removed once all services have moved to terraform-platform-modules 5.x."

        for name in s3_extension_names:
            resources = [
                "aws_s3_bucket_server_side_encryption_configuration.encryption-config",
                "aws_s3_bucket_policy.bucket-policy",
                "aws_kms_key.kms-key",
                "aws_kms_alias.s3-bucket",
            ]
            moves = [f'module.extensions.module.s3["{name}"].{resource}' for resource in resources]
            for move in moves:
                terraform["moved"].append(
                    {
                        "//": s3_comment,
                        "from": move,
                        "to": f"{move}[0]",
                    }
                )

    def _write_terraform_json(self, terraform: dict, env_dir: str):
        message = self.file_provider.mkfile(
            str(Path(env_dir).absolute()),
            "main.tf.json",
            json.dumps(terraform, indent=2),
            True,
        )
        self.io.info(message)

    def _ensure_no_hcl_manifest_file(self, env_dir):
        message = self.file_provider.delete_file(env_dir, "main.tf")
        if message:
            self.io.info(f"Manifest has moved to main.tf.json. {message}")
