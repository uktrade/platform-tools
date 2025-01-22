import json
from importlib.metadata import version
from pathlib import Path
from unittest.mock import Mock

from freezegun import freeze_time

from dbt_platform_helper.constants import SUPPORTED_AWS_PROVIDER_VERSION
from dbt_platform_helper.constants import SUPPORTED_TERRAFORM_VERSION
from dbt_platform_helper.providers.terraform_manifest import TerraformManifestProvider


@freeze_time("2025-01-16 13:00:00")
def test_generate_codebase_pipeline_config_creates_file(codebase_pipeline_config):
    mock_file_provider = Mock()
    mock_file_provider.mkfile.return_value = "File created"
    mock_echo_fn = Mock()
    template_provider = TerraformManifestProvider(mock_file_provider, mock_echo_fn)

    template_provider.generate_codebase_pipeline_config(codebase_pipeline_config, "7", set())

    assert mock_file_provider.mkfile.call_count == 1
    base_path, file_path, contents, overwrite = mock_file_provider.mkfile.call_args.args

    mock_echo_fn.assert_called_once_with("File created")

    assert base_path == str(Path(".").absolute())
    assert file_path == "terraform/codebase-pipelines/main.tf.json"
    assert overwrite

    json_content = json.loads(contents)

    exp_version = version("dbt-platform-helper")
    # Initial Comments
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
        == f"git::https://github.com/uktrade/terraform-platform-modules.git//codebase-pipelines?depth=1&ref=7"
    )
    assert module["for_each"] == "${local.all_codebases}"
    assert module["application"] == "${local.application}"
    assert module["codebase"] == "${each.key}"
    assert module["repository"] == "${each.value.repository}"
    assert (
        module["additional_ecr_repository"]
        == '${lookup(each.value, "additional_ecr_repository", null)}'
    )
    assert module["pipelines"] == "${each.value.pipelines}"
    assert module["services"] == "${each.value.services}"
    assert module["requires_image_build"] == '${lookup(each.value, "requires_image_build", true)}'
    assert (
        module["slack_channel"]
        == '${lookup(each.value, "slack_channel", "/codebuild/slack_channel_id")}'
    )
    assert module["env_config"] == "${local.environments}"


@freeze_time("2025-01-16 13:00:00")
def test_generate_codebase_pipeline_config_creates_required_imports(codebase_pipeline_config):
    file_provider = Mock()
    template_provider = TerraformManifestProvider(file_provider)

    template_provider.generate_codebase_pipeline_config(
        codebase_pipeline_config, "7", ["test_codebase"]
    )

    assert file_provider.mkfile.call_count == 1
    base_path, file_path, contents, overwrite = file_provider.mkfile.call_args.args
    assert base_path == str(Path(".").absolute())
    assert file_path == "terraform/codebase-pipelines/main.tf.json"
    assert overwrite

    json_content = json.loads(contents)

    exp_version = version("dbt-platform-helper")
    # Initial Comments
    assert "WARNING: This is an autogenerated file, not for manual editing." in json_content["//"]
    assert f"Generated by platform-helper {exp_version} / 2025-01-16 13:00:00" in json_content["//"]

    assert "import" in json_content
    assert json_content["import"]["for_each"] == '${["test_codebase"]}'
    assert json_content["import"]["id"] == "${each.value}"
    assert (
        json_content["import"]["to"]
        == "module.codebase-pipelines[each.key].aws_ecr_repository.this"
    )


@freeze_time("2025-01-16 13:00:00")
def test_generate_codebase_pipeline_config_creates_required_imports_for_two_codebases(
    two_codebase_pipeline_config,
):
    file_provider = Mock()
    template_provider = TerraformManifestProvider(file_provider)

    template_provider.generate_codebase_pipeline_config(
        two_codebase_pipeline_config, "7", ["test_codebase", "test_codebase_2"]
    )

    contents = file_provider.mkfile.call_args.args[2]

    json_content = json.loads(contents)

    exp_version = version("dbt-platform-helper")
    # Initial Comments
    assert "WARNING: This is an autogenerated file, not for manual editing." in json_content["//"]
    assert f"Generated by platform-helper {exp_version} / 2025-01-16 13:00:00" in json_content["//"]

    assert "import" in json_content
    assert json_content["import"]["for_each"] == '${["test_codebase", "test_codebase_2"]}'
    assert json_content["import"]["id"] == "${each.value}"
    assert (
        json_content["import"]["to"]
        == "module.codebase-pipelines[each.key].aws_ecr_repository.this"
    )


@freeze_time("2025-01-16 13:00:00")
def test_generate_codebase_pipeline_config_omits_include_block_if_no_codebases_provided(
    codebase_pipeline_config,
):
    file_provider = Mock()
    template_provider = TerraformManifestProvider(file_provider)

    template_provider.generate_codebase_pipeline_config(codebase_pipeline_config, "7", [])

    assert file_provider.mkfile.call_count == 1
    base_path, file_path, contents, overwrite = file_provider.mkfile.call_args.args
    assert base_path == str(Path(".").absolute())
    assert file_path == "terraform/codebase-pipelines/main.tf.json"
    assert overwrite

    json_content = json.loads(contents)

    exp_version = version("dbt-platform-helper")
    # Initial Comments
    assert "WARNING: This is an autogenerated file, not for manual editing." in json_content["//"]
    assert f"Generated by platform-helper {exp_version} / 2025-01-16 13:00:00" in json_content["//"]

    assert "import" not in json_content
