import json
from datetime import datetime
from importlib.metadata import version
from pathlib import Path
from typing import Callable

import click

from dbt_platform_helper.constants import SUPPORTED_TERRAFORM_VERSION
from dbt_platform_helper.providers.files import FileProvider


class TerraformManifestProvider:
    def __init__(
        self, file_provider: FileProvider = FileProvider(), echo: Callable[[str], None] = click.echo
    ):
        self.file_provider = file_provider
        self.echo = echo

    def generate_codebase_pipeline_config(
        self,
        platform_config: dict,
        terraform_platform_modules_version: str,
        ecr_imports: dict[str, str],
    ):
        default_account = (
            platform_config.get("environments", {})
            .get("*", {})
            .get("accounts", {})
            .get("deploy", {})
            .get("name")
        )
        terraform = {}
        self._add_header(terraform)
        self._add_locals(terraform)
        self._add_provider(terraform, default_account)
        self._add_backend(terraform, platform_config, default_account)
        self._add_codebase_pipeline_module(terraform, terraform_platform_modules_version)
        self._add_imports(terraform, ecr_imports)

        message = self.file_provider.mkfile(
            str(Path(".").absolute()),
            "terraform/codebase-pipelines/main.tf.json",
            json.dumps(terraform, indent=2),
            True,
        )
        self.echo(message)

    @staticmethod
    def _add_header(terraform: dict):
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        version_header = f"Generated by platform-helper {version('dbt-platform-helper')} / {time}."
        warning = "WARNING: This is an autogenerated file, not for manual editing."
        # The "//" key denotes a comment in terraform json.
        terraform["//"] = f"{version_header} {warning}"

    @staticmethod
    def _add_locals(terraform: dict):
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
    def _add_backend(terraform: dict, platform_config: dict, default_account: str):
        terraform["terraform"] = {
            "required_version": SUPPORTED_TERRAFORM_VERSION,
            "backend": {
                "s3": {
                    "bucket": f"terraform-platform-state-{default_account}",
                    "key": f"tfstate/application/{platform_config['application']}-codebase-pipelines.tfstate",
                    "region": "eu-west-2",
                    "encrypt": True,
                    "kms_key_id": f"alias/terraform-platform-state-s3-key-{default_account}",
                    "dynamodb_table": f"terraform-platform-lockdb-{default_account}",
                }
            },
            "required_providers": {"aws": {"source": "hashicorp/aws", "version": "~> 5"}},
        }

    @staticmethod
    def _add_codebase_pipeline_module(terraform: dict, terraform_platform_modules_version):
        source = f"git::https://github.com/uktrade/terraform-platform-modules.git//codebase-pipelines?depth=1&ref={terraform_platform_modules_version}"
        terraform["module"] = {
            "codebase-pipelines": {
                "source": source,
                "for_each": "${local.all_codebases}",
                "application": "${local.application}",
                "codebase": "${each.key}",
                "repository": "${each.value.repository}",
                "additional_ecr_repository": '${lookup(each.value, "additional_ecr_repository", null)}',
                "pipelines": "${each.value.pipelines}",
                "services": "${each.value.services}",
                "requires_image_build": "${each.value.requires_image_build}",
                "slack_channel": "${each.value.slack_channel}",
                "env_config": "${local.environments}",
            }
        }

    @staticmethod
    def _add_imports(terraform: dict, ecr_imports: dict[str, str]):
        if ecr_imports:
            terraform["import"] = {
                "for_each": "${%s}" % json.dumps(ecr_imports),
                "id": "${each.value}",
                "to": "module.codebase-pipelines[each.key].aws_ecr_repository.this",
            }
