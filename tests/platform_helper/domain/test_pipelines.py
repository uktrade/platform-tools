from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import yaml
from freezegun.api import freeze_time

from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.domain.config_validator import ConfigValidator
from dbt_platform_helper.domain.pipelines import Pipelines
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.utils.messages import abort_with_error


class PipelineMocks:
    def __init__(self, app_name):
        self.mock_config_provider = ConfigProvider(ConfigValidator())
        self.mock_terraform_manifest_provider = Mock()
        self.mock_ecr_provider = Mock()
        self.mock_echo = Mock()
        self.mock_abort = abort_with_error
        self.mock_git_remote = Mock()
        self.mock_git_remote.return_value = "uktrade/test-app-deploy"
        self.mock_codestar = Mock()
        self.mock_codestar.return_value = (
            f"arn:aws:codestar-connections:eu-west-2:1234567:connection/{app_name}"
        )
        self.mock_ecr_provider.get_ecr_repo_names.return_value = []

    def params(self):
        return {
            "config_provider": self.mock_config_provider,
            "terraform_manifest_provider": self.mock_terraform_manifest_provider,
            "ecr_provider": self.mock_ecr_provider,
            "echo": self.mock_echo,
            "abort": self.mock_abort,
            "get_git_remote": self.mock_git_remote,
            "get_codestar_arn": self.mock_codestar,
        }


def test_pipeline_generate_with_empty_platform_config_yml_outputs_warning():
    mock_config_provider = Mock()
    app_name = "my-app"
    mock_config_provider.load_and_validate_platform_config.return_value = {"application": app_name}
    mocks = PipelineMocks(app_name)
    mocks.mock_config_provider = mock_config_provider
    pipelines = Pipelines(**mocks.params())

    pipelines.generate(None, None)

    mocks.mock_echo.assert_called_once_with(
        "No pipelines defined: nothing to do.", err=True, fg="yellow"
    )


def test_pipeline_generate_with_non_empty_platform_config_but_no_pipelines_outputs_warning():
    mock_config_provider = Mock()
    mock_config_provider.load_and_validate_platform_config.return_value = {"environments": {}}
    mocks = PipelineMocks("app-name")
    mocks.mock_config_provider = mock_config_provider
    pipelines = Pipelines(**mocks.params())

    pipelines.generate(None, None)

    mocks.mock_echo.assert_called_once_with(
        "No pipelines defined: nothing to do.", err=True, fg="yellow"
    )


@freeze_time("2024-10-28 12:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@pytest.mark.parametrize(
    "cli_terraform_platform_version, config_terraform_platform_version, expected_terraform_platform_version, cli_demodjango_branch, expected_demodjango_branch",
    [  # config_terraform_platform_version sets the platform-config.yml to include the TPM version at platform-config.yml/default_versions/terraform-platform-modules
        ("5", True, "5", None, None),  # Case with cli_terraform_platform_version
        (
            None,
            True,
            "4.0.0",
            "demodjango-branch",
            "demodjango-branch",
        ),  # Case with config_terraform_platform_version and specific branch
        (None, True, "4.0.0", None, None),  # Case with config_terraform_platform_version
        (
            None,
            None,
            DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION,
            None,
            None,
        ),  # Case with default TPM version and without branch, defaults
    ],
)
def test_generate_pipeline_command_generate_terraform_files_for_environment_pipeline_manifest(
    fakefs,
    cli_terraform_platform_version,
    config_terraform_platform_version,
    expected_terraform_platform_version,
    cli_demodjango_branch,
    expected_demodjango_branch,
    platform_config_for_env_pipelines,
):

    app_name = "test-app"
    if config_terraform_platform_version:
        platform_config_for_env_pipelines["default_versions"] = {
            "terraform-platform-modules": "4.0.0"
        }
    fakefs.create_file(PLATFORM_CONFIG_FILE, contents=yaml.dump(platform_config_for_env_pipelines))
    mocks = PipelineMocks(app_name)
    pipelines = Pipelines(**mocks.params())

    pipelines.generate(cli_terraform_platform_version, cli_demodjango_branch)

    assert_terraform(
        app_name,
        "platform-sandbox-test",
        expected_terraform_platform_version,
        expected_demodjango_branch,
    )
    assert_terraform(
        app_name,
        "platform-prod-test",
        expected_terraform_platform_version,
        expected_demodjango_branch,
    )


@pytest.mark.parametrize(
    "cli_version, exp_version", [("6", "6"), (None, DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION)]
)
def test_generate_calls_generate_codebase_pipeline_config_with_expected_tpm_version(
    cli_version, exp_version, codebase_pipeline_config_for_1_pipeline_and_2_run_groups, fakefs
):
    app_name = "test-app"
    fakefs.create_file(
        PLATFORM_CONFIG_FILE,
        contents=yaml.dump(codebase_pipeline_config_for_1_pipeline_and_2_run_groups),
    )
    mocks = PipelineMocks(app_name)
    pipelines = Pipelines(**mocks.params())

    pipelines.generate(cli_version, None)

    mock_t_m_p = mocks.mock_terraform_manifest_provider
    mock_t_m_p.generate_codebase_pipeline_config.assert_called_once_with(
        codebase_pipeline_config_for_1_pipeline_and_2_run_groups, exp_version, {}
    )


def test_generate_pipeline_generates_codebase_pipeline_with_imports(
    codebase_pipeline_config_for_2_pipelines_and_1_run_group, fakefs
):
    app_name = "test-app"
    fakefs.create_file(
        PLATFORM_CONFIG_FILE,
        contents=yaml.dump(codebase_pipeline_config_for_2_pipelines_and_1_run_group),
    )
    mocks = PipelineMocks(app_name)
    mocks.mock_ecr_provider.get_ecr_repo_names.return_value = [
        "my-app/test_codebase",
        "some-other-repo",
        "my-app/test_codebase_2",
        "yet-another-repo",
    ]
    pipelines = Pipelines(**mocks.params())

    pipelines.generate("6", None)

    mock_t_m_p = mocks.mock_terraform_manifest_provider
    mock_t_m_p.generate_codebase_pipeline_config.assert_called_once_with(
        codebase_pipeline_config_for_2_pipelines_and_1_run_group,
        "6",
        {"test_codebase": "my-app/test_codebase", "test_codebase_2": "my-app/test_codebase_2"},
    )


def assert_terraform(app_name, aws_account, expected_version, expected_branch):
    expected_files_dir = Path(f"terraform/environment-pipelines/{aws_account}/main.tf")
    assert expected_files_dir.exists()
    content = expected_files_dir.read_text()

    assert "# WARNING: This is an autogenerated file, not for manual editing." in content
    assert "# Generated by platform-helper v0.1-TEST / 2024-10-28 12:00:00" in content
    assert f'profile                  = "{aws_account}"' in content
    assert (
        f"git::https://github.com/uktrade/terraform-platform-modules.git//environment-pipelines?depth=1&ref={expected_version}"
        in content
    )
    assert f'application         = "{app_name}"' in content
    expected_branch_value = expected_branch if expected_branch else "each.value.branch"
    assert f"branch              = {expected_branch_value} in content"
