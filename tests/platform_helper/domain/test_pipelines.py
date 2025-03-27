import re
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import yaml
from freezegun.api import freeze_time

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.domain.pipelines import Pipelines
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.legacy_versions import LegacyVersionsProvider


class PipelineMocks:
    def __init__(self, app_name):
        self.mock_config_provider = ConfigProvider(ConfigValidator())
        self.mock_terraform_manifest_provider = Mock()
        self.mock_ecr_provider = Mock()
        self.io = Mock()
        self.io.abort_with_error = Mock(side_effect=SystemExit(1))
        self.mock_git_remote = Mock()
        self.mock_git_remote.return_value = "uktrade/test-app-deploy"
        self.mock_codestar = Mock()
        self.mock_codestar.return_value = (
            f"arn:aws:codestar-connections:eu-west-2:1234567:connection/{app_name}"
        )
        self.mock_ecr_provider.get_ecr_repo_names.return_value = []
        self.mock_legacy_versions_provider = LegacyVersionsProvider(io=self.io)

    def params(self):
        return {
            "config_provider": self.mock_config_provider,
            "terraform_manifest_provider": self.mock_terraform_manifest_provider,
            "ecr_provider": self.mock_ecr_provider,
            "io": self.io,
            "get_git_remote": self.mock_git_remote,
            "get_codestar_arn": self.mock_codestar,
            "legacy_versions_provider": self.mock_legacy_versions_provider,
        }


def test_pipeline_generate_with_empty_platform_config_yml_outputs_warning():
    mock_config_provider = Mock()
    app_name = "my-app"
    mock_config_provider.load_and_validate_platform_config.return_value = {"application": app_name}
    mocks = PipelineMocks(app_name)
    mocks.mock_config_provider = mock_config_provider
    pipelines = Pipelines(**mocks.params())

    pipelines.generate(None, None, None)

    mocks.io.warn.assert_called_once_with("No pipelines defined: nothing to do.")


def test_pipeline_generate_with_non_empty_platform_config_but_no_pipelines_outputs_warning():
    mock_config_provider = Mock()
    mock_config_provider.load_and_validate_platform_config.return_value = {"environments": {}}
    mocks = PipelineMocks("app-name")
    mocks.mock_config_provider = mock_config_provider
    pipelines = Pipelines(**mocks.params())

    pipelines.generate(None, None, None)

    mocks.io.warn.assert_called_once_with("No pipelines defined: nothing to do.")


@freeze_time("2024-10-28 12:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@pytest.mark.parametrize(
    "cli_terraform_platform_modules_version, cli_platform_helper_version, config_platform_helper_version, expected_platform_helper_version, cli_demodjango_branch, expected_demodjango_branch",
    [  # config_platform_helper_version sets the platform-config.yml to include the platform-helper version at platform-config.yml/default_versions/platform-helper
        ("7", "13", True, "13", None, None),  # Case with cli_platform_helper_version
        (
            "7",
            None,
            True,
            "12.0.0",
            "demodjango-branch",
            "demodjango-branch",
        ),  # Case with config_platform_helper_version and specific branch
        ("7", None, True, "12.0.0", None, None),
        (None, None, True, "12.0.0", None, None),
    ],
)
def test_generate_pipeline_command_generate_terraform_files_for_environment_pipeline_manifest(
    fakefs,
    cli_terraform_platform_modules_version,
    cli_platform_helper_version,
    config_platform_helper_version,
    expected_platform_helper_version,
    cli_demodjango_branch,
    expected_demodjango_branch,
    platform_config_for_env_pipelines,
):

    app_name = "test-app"
    if config_platform_helper_version:
        platform_config_for_env_pipelines["default_versions"] = {"platform-helper": "12.0.0"}
    fakefs.create_file(PLATFORM_CONFIG_FILE, contents=yaml.dump(platform_config_for_env_pipelines))
    mocks = PipelineMocks(app_name)
    pipelines = Pipelines(**mocks.params())

    pipelines.generate(
        cli_terraform_platform_modules_version, cli_platform_helper_version, cli_demodjango_branch
    )

    assert_terraform(
        app_name,
        "platform-sandbox-test",
        expected_platform_helper_version,
        expected_demodjango_branch,
    )
    assert_terraform(
        app_name,
        "platform-prod-test",
        expected_platform_helper_version,
        expected_demodjango_branch,
    )


@freeze_time("2024-10-28 12:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
def test_generate_pipeline_generates_expected_terraform_manifest_when_no_deploy_repository_key(
    fakefs,
    platform_config_for_env_pipelines,
):

    app_name = "test-app"
    # deploy_repository key set on test_fixture so remove it
    platform_config_for_env_pipelines.pop("deploy_repository")
    fakefs.create_file(PLATFORM_CONFIG_FILE, contents=yaml.dump(platform_config_for_env_pipelines))
    mocks = PipelineMocks(app_name)
    pipelines = Pipelines(**mocks.params())

    pipelines.generate("cli-tpm-version", "an-unimportant-platform-version", "a-branch")

    expected_files_dir = Path(f"terraform/environment-pipelines/platform-prod-test/main.tf")
    assert expected_files_dir.exists()
    content = expected_files_dir.read_text()

    warn_calls = [call.args[0] for call in mocks.io.warn.mock_calls]
    assert (
        "No `deploy_repository` key set in platform-config.yml, this will become a required key. See full platform config reference in the docs: https://platform.readme.trade.gov.uk/reference/platform-config-yml/#core-configuration"
        in warn_calls
    )

    assert re.search(r'repository += +"uktrade/test-app-deploy"', content)


@freeze_time("2024-10-28 12:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
def test_generate_pipeline_creates_warning_when_deprecated_terraform_platform_modules_version_cli_flag_is_present(
    fakefs,
    platform_config_for_env_pipelines,
):
    app_name = "test-app"
    fakefs.create_file(
        PLATFORM_CONFIG_FILE,
        contents=yaml.dump(platform_config_for_env_pipelines),
    )
    mocks = PipelineMocks(app_name)
    pipelines = Pipelines(**mocks.params())

    pipelines.generate(
        "terraform_platform_modules_version", "platform-helper-version", "any-branch"
    )

    expected_files_dir = Path(f"terraform/environment-pipelines/platform-prod-test/main.tf")
    assert expected_files_dir.exists()
    content = expected_files_dir.read_text()

    mocks.io.warn.assert_called_once_with(
        "The `--terraform-platform-modules-version` flag for the pipeline generate command is deprecated. "
        "Please use the `--platform-helper-version` flag instead.\n"
    )
    assert re.search(r'repository += +"uktrade/test-app-weird-name-deploy"', content)


@freeze_time("2024-10-28 12:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
def test_generate_pipeline_creates_warning_when_deprecated_terraform_platform_repository_key_present_in_default_config(
    fakefs,
    platform_config_for_env_pipelines_with_deprecated_tpm_default_versions,
):
    app_name = "test-app"
    fakefs.create_file(
        PLATFORM_CONFIG_FILE,
        contents=yaml.dump(platform_config_for_env_pipelines_with_deprecated_tpm_default_versions),
    )
    mocks = PipelineMocks(app_name)
    pipelines = Pipelines(**mocks.params())

    pipelines.generate(None, "platform-helper-version", "any-branch")

    expected_files_dir = Path(f"terraform/environment-pipelines/platform-prod-test/main.tf")
    assert expected_files_dir.exists()
    content = expected_files_dir.read_text()

    mocks.io.warn.assert_called_once_with(
        "The `terraform-platform-modules` key set in the platform-config.yml file in the following location: `default_versions: terraform-platform-modules` is now deprecated. "
        "Please use the `default_versions: platform-helper` value instead. "
        "See full platform config reference in the docs: "
        "https://platform.readme.trade.gov.uk/reference/platform-config-yml/#core-configuration.\n"
    )
    assert re.search(r'repository += +"uktrade/test-app-weird-name-deploy"', content)


@freeze_time("2024-10-28 12:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
def test_generate_pipeline_creates_warning_when_deprecated_terraform_platform_repository_key_present_in_environment_config(
    fakefs,
    platform_config_for_env_pipelines,
):
    app_name = "test-app"
    # Adding the deprecated TPM keyword to config file
    platform_config_for_env_pipelines["environments"]["dev"]["versions"] = {
        "terraform-platform-modules": "12.0.0"
    }
    fakefs.create_file(PLATFORM_CONFIG_FILE, contents=yaml.dump(platform_config_for_env_pipelines))
    mocks = PipelineMocks(app_name)
    pipelines = Pipelines(**mocks.params())

    pipelines.generate(None, "platform-helper-version", "any-branch")

    expected_files_dir = Path(f"terraform/environment-pipelines/platform-prod-test/main.tf")
    assert expected_files_dir.exists()
    content = expected_files_dir.read_text()

    mocks.io.warn.assert_called_once_with(
        "The `terraform-platform-modules` key set in the platform-config.yml file in the following location:  `environments: <env>: versions: terraform-platform-modules` is now deprecated. "
        "Please use the `default_versions: platform-helper` value instead. "
        "See full platform config reference in the docs: "
        "https://platform.readme.trade.gov.uk/reference/platform-config-yml/#core-configuration.\n"
    )
    assert re.search(r'repository += +"uktrade/test-app-weird-name-deploy"', content)


def test_generate_calls_generate_codebase_pipeline_config_with_expected_tpm_version(
    codebase_pipeline_config_for_1_pipeline_and_2_run_groups,
    fakefs,
):
    cli_tpm_version = ("7",)
    cli_platform_helper_version = "13"
    exp_version = "13"
    app_name = "test-app"
    fakefs.create_file(
        PLATFORM_CONFIG_FILE,
        contents=yaml.dump(codebase_pipeline_config_for_1_pipeline_and_2_run_groups),
    )
    mocks = PipelineMocks(app_name)
    pipelines = Pipelines(**mocks.params())

    pipelines.generate(cli_tpm_version, cli_platform_helper_version, None)

    mock_t_m_p = mocks.mock_terraform_manifest_provider
    mock_t_m_p.generate_codebase_pipeline_config.assert_called_once_with(
        codebase_pipeline_config_for_1_pipeline_and_2_run_groups,
        exp_version,
        {},
        "uktrade/my-app-deploy",
    )


def test_generate_calls_generate_codebase_pipeline_config_with_imports(
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

    pipelines.generate("7", "13", None)

    mock_t_m_p = mocks.mock_terraform_manifest_provider
    mock_t_m_p.generate_codebase_pipeline_config.assert_called_once_with(
        codebase_pipeline_config_for_2_pipelines_and_1_run_group,
        "13",
        {"test_codebase": "my-app/test_codebase", "test_codebase_2": "my-app/test_codebase_2"},
        "uktrade/my-app-deploy",
    )


def assert_terraform(app_name, aws_account, expected_version, expected_branch):
    expected_files_dir = Path(f"terraform/environment-pipelines/{aws_account}/main.tf")
    assert expected_files_dir.exists()
    content = expected_files_dir.read_text()

    assert "# WARNING: This is an autogenerated file, not for manual editing." in content
    assert "# Generated by platform-helper v0.1-TEST / 2024-10-28 12:00:00" in content
    assert f'profile                  = "{aws_account}"' in content
    assert re.search(r'repository += +"uktrade/test-app-weird-name-deploy"', content)
    assert (
        f"git::https://github.com/uktrade/platform-tools.git//terraform/environment-pipelines?depth=1&ref={expected_version}"
        in content
    )
    assert f'application         = "{app_name}"' in content
    expected_branch_value = expected_branch if expected_branch else "each.value.branch"
    assert f"branch              = {expected_branch_value} in content"
