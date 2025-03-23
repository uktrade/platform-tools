import json
from importlib.metadata import version
from pathlib import Path
from unittest.mock import Mock

import pytest
from freezegun import freeze_time

from dbt_platform_helper.constants import SUPPORTED_AWS_PROVIDER_VERSION
from dbt_platform_helper.constants import SUPPORTED_TERRAFORM_VERSION
from dbt_platform_helper.providers.terraform_manifest import TerraformManifestProvider
from tests.platform_helper.conftest import (
    codebase_pipeline_config_for_1_pipeline_and_2_run_groups,
)
from tests.platform_helper.conftest import (
    codebase_pipeline_config_for_2_pipelines_and_1_run_group,
)


@freeze_time("2025-01-16 13:00:00")
def test_generate_codebase_pipeline_config_creates_file(
    codebase_pipeline_config_for_1_pipeline_and_2_run_groups,
):
    mock_file_provider = Mock()
    mock_file_provider.mkfile.return_value = "File created"
    mock_io = Mock()
    template_provider = TerraformManifestProvider(mock_file_provider, mock_io)

    template_provider.generate_codebase_pipeline_config(
        codebase_pipeline_config_for_1_pipeline_and_2_run_groups,
        platform_helper_version="13",
        ecr_imports={},
        deploy_repository="uktrade/my-app-deploy",
    )

    mock_file_provider.mkfile.assert_called_once()
    base_path, file_path, contents, overwrite = mock_file_provider.mkfile.call_args.args

    mock_io.info.assert_called_with("File created")

    assert base_path == str(Path("terraform/codebase-pipelines").absolute())
    assert file_path == "main.tf.json"
    assert overwrite

    json_content = json.loads(contents)

    exp_version = version("dbt-platform-helper")
    assert "WARNING: This is an autogenerated file, not for manual editing." in json_content["//"]
    assert f"Generated by platform-helper {exp_version} / 2025-01-16 13:00:00" in json_content["//"]

    local = json_content["locals"]
    assert local["platform_config"] == '${yamldecode(file("../../platform-config.yml"))}'
    assert local["application"] == '${local.platform_config["application"]}'
    assert local["all_codebases"] == '${local.platform_config["codebase_pipelines"]}'
    assert local["environments"] == '${local.platform_config["environments"]}'

    aws_provider = json_content["provider"]["aws"]
    assert aws_provider["region"] == "eu-west-2"
    assert aws_provider["profile"] == "non-prod-acc"
    assert aws_provider["alias"] == "non-prod-acc"
    assert aws_provider["shared_credentials_files"] == ["~/.aws/config"]

    terraform = json_content["terraform"]
    assert terraform["required_version"] == SUPPORTED_TERRAFORM_VERSION

    s3_backend = terraform["backend"]["s3"]
    assert s3_backend["bucket"] == "terraform-platform-state-non-prod-acc"
    assert s3_backend["key"] == "tfstate/application/my-app-codebase-pipelines.tfstate"
    assert s3_backend["region"] == "eu-west-2"
    assert s3_backend["encrypt"] is True
    assert s3_backend["kms_key_id"] == "alias/terraform-platform-state-s3-key-non-prod-acc"
    assert s3_backend["dynamodb_table"] == "terraform-platform-lockdb-non-prod-acc"

    aws_req_provider = terraform["required_providers"]["aws"]
    assert aws_req_provider["source"] == "hashicorp/aws"
    assert aws_req_provider["version"] == SUPPORTED_AWS_PROVIDER_VERSION

    module = json_content["module"]["codebase-pipelines"]
    assert (
        module["source"]
        == f"git::https://github.com/uktrade/platform-tools.git//terraform/codebase-pipelines?depth=1&ref=13"
    )
    assert module["for_each"] == "${local.all_codebases}"
    assert module["application"] == "${local.application}"
    assert module["codebase"] == "${each.key}"
    assert module["repository"] == "${each.value.repository}"
    assert module["deploy_repository"] == "uktrade/my-app-deploy"
    assert (
        module["deploy_repository_branch"]
        == '${lookup(each.value, "deploy_repository_branch", "main")}'
    )
    assert (
        module["additional_ecr_repository"]
        == '${lookup(each.value, "additional_ecr_repository", null)}'
    )
    assert module["pipelines"] == '${lookup(each.value, "pipelines", [])}'
    assert module["services"] == "${each.value.services}"
    assert module["requires_image_build"] == '${lookup(each.value, "requires_image_build", true)}'
    assert (
        module["slack_channel"]
        == '${lookup(each.value, "slack_channel", "/codebuild/slack_oauth_channel")}'
    )
    assert module["env_config"] == "${local.environments}"


@freeze_time("2025-01-16 13:00:00")
@pytest.mark.parametrize(
    "config_fixture, exp_imports",
    [
        (codebase_pipeline_config_for_1_pipeline_and_2_run_groups.__name__, '${["test_codebase"]}'),
        (
            codebase_pipeline_config_for_2_pipelines_and_1_run_group.__name__,
            '${["test_codebase", "test_codebase_2"]}',
        ),
    ],
)
def test_generate_codebase_pipeline_config_creates_required_imports(
    config_fixture, exp_imports, request
):
    mock_file_provider = Mock()
    template_provider = TerraformManifestProvider(mock_file_provider)
    config = request.getfixturevalue(config_fixture)

    template_provider.generate_codebase_pipeline_config(
        config,
        platform_helper_version="13",
        ecr_imports={"application": "test_project/application"},
        deploy_repository="uktrade/my-app-deploy",
    )

    mock_file_provider.mkfile.assert_called_once()
    json_content = json.loads(mock_file_provider.mkfile.call_args.args[2])
    assert "import" in json_content
    assert json_content["import"]["for_each"] == '${{"application": "test_project/application"}}'
    assert json_content["import"]["id"] == "${each.value}"
    assert (
        json_content["import"]["to"]
        == "module.codebase-pipelines[each.key].aws_ecr_repository.this"
    )


@freeze_time("2025-01-16 13:00:00")
def test_generate_codebase_pipeline_config_omits_import_block_if_no_codebases_provided(
    codebase_pipeline_config_for_1_pipeline_and_2_run_groups,
):
    mock_file_provider = Mock()
    template_provider = TerraformManifestProvider(mock_file_provider)

    template_provider.generate_codebase_pipeline_config(
        codebase_pipeline_config_for_1_pipeline_and_2_run_groups,
        platform_helper_version="13",
        ecr_imports={},
        deploy_repository="uktrade/my-app-deploy",
    )

    mock_file_provider.mkfile.assert_called_once()
    json_content = json.loads(mock_file_provider.mkfile.call_args.args[2])
    assert "import" not in json_content


@freeze_time("2025-01-16 13:00:00")
@pytest.mark.parametrize(
    "app, env, platform_helper_version, expected_aws_account",
    [
        ("app1", "dev", "13", "non-prod-acc"),
        ("app2", "staging", "12", "non-prod-acc"),
        ("app3", "prod", "13", "prod-acc"),
    ],
)
def test_generate_environment_config_creates_file(
    platform_env_config, app, env, platform_helper_version, expected_aws_account
):
    platform_env_config["application"] = app
    mock_file_provider = Mock()
    mock_file_provider.mkfile.return_value = "File created"
    mock_file_provider.delete_file.return_value = (
        f"terraform/environments/{env}/main.tf has been deleted"
    )
    mock_io = Mock()
    template_provider = TerraformManifestProvider(mock_file_provider, mock_io)

    template_provider.generate_environment_config(
        platform_env_config, env=env, platform_helper_version=platform_helper_version
    )

    mock_file_provider.mkfile.assert_called_once()
    base_path, file_path, contents, overwrite = mock_file_provider.mkfile.call_args.args

    messages = [call.args[0] for call in mock_io.info.call_args_list]
    assert (
        messages[0]
        == f"Manifest has moved to main.tf.json. terraform/environments/{env}/main.tf has been deleted"
    )
    assert messages[1] == "File created"
    mock_file_provider.delete_file.assert_called_with(f"terraform/environments/{env}", "main.tf")

    assert base_path == str(Path(f"terraform/environments/{env}").absolute())
    assert file_path == "main.tf.json"
    assert overwrite

    json_content = json.loads(contents)

    exp_version = version("dbt-platform-helper")
    assert "WARNING: This is an autogenerated file, not for manual editing." in json_content["//"]
    assert f"Generated by platform-helper {exp_version} / 2025-01-16 13:00:00" in json_content["//"]

    local = json_content["locals"]
    assert local["config"] == '${yamldecode(file("../../../platform-config.yml"))}'
    assert local["environments"] == '${local.config["environments"]}'
    assert (
        local["env_config"]
        == '${{for name, config in local.environments: name => merge(lookup(local.environments, "*", {}), config)}}'
    )
    assert local["args"] == {
        "application": platform_env_config["application"],
        "services": '${local.config["extensions"]}',
        "env_config": "${local.env_config}",
    }

    terraform = json_content["terraform"]
    assert terraform["required_version"] == SUPPORTED_TERRAFORM_VERSION

    s3_backend = terraform["backend"]["s3"]
    assert s3_backend["bucket"] == f"terraform-platform-state-{expected_aws_account}"
    assert s3_backend["key"] == f"tfstate/application/{app}-{env}.tfstate"
    assert s3_backend["region"] == "eu-west-2"
    assert s3_backend["encrypt"] is True
    assert (
        s3_backend["kms_key_id"] == f"alias/terraform-platform-state-s3-key-{expected_aws_account}"
    )
    assert s3_backend["dynamodb_table"] == f"terraform-platform-lockdb-{expected_aws_account}"

    aws_req_provider = terraform["required_providers"]["aws"]
    assert aws_req_provider["source"] == "hashicorp/aws"
    assert aws_req_provider["version"] == SUPPORTED_AWS_PROVIDER_VERSION

    module = json_content["module"]["extensions"]
    assert (
        module["source"]
        == f"git::https://github.com/uktrade/platform-tools.git//terraform/extensions?depth=1&ref={platform_helper_version}"
    )
    assert module["args"] == "${local.args}"
    assert module["environment"] == env

    moved = json_content["moved"]
    assert len(moved) == 1
    assert (
        moved[0]["//"]
        == "Moved extensions-tf to just extensions - this block tells terraform this. Can be removed once all services have moved to the new naming."
    )
    assert moved[0]["from"] == "module.extensions-tf"
    assert moved[0]["to"] == "module.extensions"


def test_generate_environment_config_with_multiple_extensions_adds_moved_blocks_for_s3(
    platform_env_config,
):
    platform_env_config["application"] = "test-app"
    platform_env_config["extensions"] = {
        "test-s3-1": {"type": "s3", "services": ["web"], "environments": {}},
        "test-s3-2": {"type": "s3", "services": ["web"], "environments": {}},
        "test-monitoring": {"type": "monitoring", "environments": {}},
    }
    mock_file_provider = Mock()
    mock_file_provider.mkfile.return_value = "File created"
    mock_io = Mock()
    template_provider = TerraformManifestProvider(mock_file_provider, mock_io)

    template_provider.generate_environment_config(
        platform_env_config, env="dev", platform_helper_version="13"
    )

    _, _, contents, _ = mock_file_provider.mkfile.call_args.args
    json_content = json.loads(contents)
    moved = json_content["moved"]
    assert (
        moved[0]["//"]
        == "Moved extensions-tf to just extensions - this block tells terraform this. Can be removed once all services have moved to the new naming."
    )
    assert moved[0]["from"] == "module.extensions-tf"
    assert moved[0]["to"] == "module.extensions"
    expected_message = "S3 bucket resources are now indexed. Can be removed once all services have moved to terraform-platform-modules 5.x."
    assert moved[1]["//"] == expected_message
    assert (
        moved[1]["from"]
        == f'module.extensions.module.s3["test-s3-1"].aws_s3_bucket_server_side_encryption_configuration.encryption-config'
    )
    assert (
        moved[1]["to"]
        == f'module.extensions.module.s3["test-s3-1"].aws_s3_bucket_server_side_encryption_configuration.encryption-config[0]'
    )
    assert moved[2]["//"] == expected_message
    assert (
        moved[2]["from"]
        == f'module.extensions.module.s3["test-s3-1"].aws_s3_bucket_policy.bucket-policy'
    )
    assert (
        moved[2]["to"]
        == f'module.extensions.module.s3["test-s3-1"].aws_s3_bucket_policy.bucket-policy[0]'
    )
    assert moved[3]["//"] == expected_message
    assert moved[3]["from"] == f'module.extensions.module.s3["test-s3-1"].aws_kms_key.kms-key'
    assert moved[3]["to"] == f'module.extensions.module.s3["test-s3-1"].aws_kms_key.kms-key[0]'
    assert moved[4]["//"] == expected_message
    assert moved[4]["from"] == f'module.extensions.module.s3["test-s3-1"].aws_kms_alias.s3-bucket'
    assert moved[4]["to"] == f'module.extensions.module.s3["test-s3-1"].aws_kms_alias.s3-bucket[0]'
    assert moved[5]["//"] == expected_message
    assert (
        moved[5]["from"]
        == f'module.extensions.module.s3["test-s3-2"].aws_s3_bucket_server_side_encryption_configuration.encryption-config'
    )
    assert (
        moved[5]["to"]
        == f'module.extensions.module.s3["test-s3-2"].aws_s3_bucket_server_side_encryption_configuration.encryption-config[0]'
    )
    assert moved[6]["//"] == expected_message
    assert (
        moved[6]["from"]
        == f'module.extensions.module.s3["test-s3-2"].aws_s3_bucket_policy.bucket-policy'
    )
    assert (
        moved[6]["to"]
        == f'module.extensions.module.s3["test-s3-2"].aws_s3_bucket_policy.bucket-policy[0]'
    )
    assert moved[7]["//"] == expected_message
    assert moved[7]["from"] == f'module.extensions.module.s3["test-s3-2"].aws_kms_key.kms-key'
    assert moved[7]["to"] == f'module.extensions.module.s3["test-s3-2"].aws_kms_key.kms-key[0]'
    assert moved[8]["//"] == expected_message
    assert moved[8]["from"] == f'module.extensions.module.s3["test-s3-2"].aws_kms_alias.s3-bucket'
    assert moved[8]["to"] == f'module.extensions.module.s3["test-s3-2"].aws_kms_alias.s3-bucket[0]'


def test_generate_environment_config_when_old_manifest_not_deleted_does_not_output_deleted_message(
    platform_env_config,
):
    platform_env_config["application"] = "test-app"
    mock_file_provider = Mock()
    mock_file_provider.mkfile.return_value = "File created"
    mock_file_provider.delete_file.return_value = None
    mock_io = Mock()
    template_provider = TerraformManifestProvider(mock_file_provider, mock_io)

    template_provider.generate_environment_config(
        platform_env_config, env="dev", platform_helper_version="13"
    )

    mock_io.info.assert_called_once_with("File created")
