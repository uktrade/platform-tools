import re
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import create_autospec
from unittest.mock import patch

import hcl2
import pytest
import yaml
from freezegun.api import freeze_time

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_OVERRIDE_KEY
from dbt_platform_helper.constants import (
    TERRAFORM_CODEBASE_PIPELINES_MODULE_SOURCE_OVERRIDE_ENV_VAR,
)
from dbt_platform_helper.constants import (
    TERRAFORM_ENVIRONMENT_PIPELINES_MODULE_SOURCE_OVERRIDE_ENV_VAR,
)
from dbt_platform_helper.domain.pipelines import Pipelines
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.entities.semantic_version import SemanticVersion
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.version import InstalledVersionProvider
from tests.platform_helper.domain.test_versioning import PlatformHelperVersioningMocks


class PipelineMocks:
    def __init__(self, app_name):
        mock_installed_version_provider = create_autospec(
            spec=InstalledVersionProvider, spec_set=True
        )
        mock_installed_version_provider.get_semantic_version.return_value = SemanticVersion(
            14, 0, 0
        )
        self.mock_config_provider = ConfigProvider(
            Mock(), installed_version_provider=mock_installed_version_provider
        )
        self.mock_terraform_manifest_provider = Mock()
        self.mock_ecr_provider = Mock()
        mock_io = Mock()
        self.io = mock_io
        self.io.abort_with_error = Mock(side_effect=SystemExit(1))
        self.mock_git_remote = Mock()
        self.mock_git_remote.return_value = "uktrade/test-app-deploy"
        self.mock_ecr_provider.get_ecr_repo_names.return_value = []
        platform_helper_versioning_mocks = PlatformHelperVersioningMocks()
        platform_helper_versioning_mocks.mock_config_provider = self.mock_config_provider
        platform_helper_versioning_mocks.mock_io = mock_io
        self.mock_platform_helper_versioning = PlatformHelperVersioning(
            **platform_helper_versioning_mocks.params()
        )

    def params(self):
        return {
            "config_provider": self.mock_config_provider,
            "terraform_manifest_provider": self.mock_terraform_manifest_provider,
            "ecr_provider": self.mock_ecr_provider,
            "io": self.io,
            "get_git_remote": self.mock_git_remote,
            "platform_helper_versioning": self.mock_platform_helper_versioning,
        }


def test_pipeline_generate_with_empty_platform_config_yml_outputs_warning():
    mock_config_provider = Mock()
    app_name = "my-app"
    mock_config_provider.load_and_validate_platform_config.return_value = {"application": app_name}
    mocks = PipelineMocks(app_name)
    mocks.mock_config_provider = mock_config_provider
    pipelines = Pipelines(**mocks.params())

    pipelines.generate(None)

    mocks.io.warn.assert_called_once_with("No pipelines defined: nothing to do.")


def test_pipeline_generate_with_auto_errors_when_expected_env_vars_are_not_set():
    mock_config = {
        "application": "anything",
        "default_versions": {"platform-helper": "auto"},
    }
    mock_config_provider = Mock()
    mock_config_provider.load_and_validate_platform_config.return_value = mock_config
    mock_config_provider.load_unvalidated_config_file.return_value = mock_config
    mocks = PipelineMocks("anything")
    mocks.mock_config_provider = mock_config_provider
    mocks.mock_platform_helper_versioning.config_provider = mock_config_provider

    mock_env_var_provider = {}

    mocks.mock_platform_helper_versioning.environment_variable_provider = mock_env_var_provider

    pipelines = Pipelines(**mocks.params())

    with pytest.raises(SystemExit):
        pipelines.generate(None)


def test_pipeline_generate_with_auto_error_is_bypassed_if_versioning_check_override_is_allowed():
    mock_config = {
        "application": "anything",
        "default_versions": {"platform-helper": "auto"},
    }
    mock_config_provider = Mock()
    mock_config_provider.load_and_validate_platform_config.return_value = mock_config
    mock_config_provider.load_unvalidated_config_file.return_value = mock_config
    mocks = PipelineMocks("anything")
    mocks.mock_config_provider = mock_config_provider
    mocks.mock_platform_helper_versioning.config_provider = mock_config_provider

    mock_env_var_provider = {}
    mocks.mock_platform_helper_versioning.environment_variable_provider = mock_env_var_provider

    mocks.mock_platform_helper_versioning.allow_override_of_versioning_checks = True

    Pipelines(**mocks.params()).generate(None)

    warn_calls = [call.args[0] for call in mocks.io.warn.mock_calls]
    assert (
        "You are on managed upgrades. Generate commands should only be running inside a pipeline environment."
        in warn_calls
    )


def test_pipeline_generate_with_non_empty_platform_config_but_no_pipelines_outputs_warning():
    mock_config_provider = Mock()
    mock_config_provider.load_and_validate_platform_config.return_value = {"environments": {}}
    mocks = PipelineMocks("app-name")
    mocks.mock_config_provider = mock_config_provider
    pipelines = Pipelines(**mocks.params())

    pipelines.generate(None)

    mocks.io.warn.assert_called_once_with("No pipelines defined: nothing to do.")


@freeze_time("2024-10-28 12:00:00")
@patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@pytest.mark.parametrize(
    "use_environment_variable_platform_helper_version, is_auto, expected_platform_helper_version, cli_demodjango_branch, expected_demodjango_branch, expected_pinned_version, module_source_override",
    [  # config_platform_helper_version sets the platform-config.yml to include the platform-helper version at platform-config.yml/default_versions/platform-helper
        (False, False, "14.0.0", "demodjango-branch", "demodjango-branch", None, "../local/path/"),
        (False, False, "14.0.0", None, None, None, None),
        (True, False, "test-branch", None, None, None, "../local/path/"),
        (True, False, "test-branch", None, None, None, None),
        (True, True, "test-branch", None, None, "test-branch", None),
    ],
)
def test_pipeline_generate_command_generate_terraform_files_for_environment_pipeline_manifest(
    fakefs,
    use_environment_variable_platform_helper_version,
    is_auto,
    expected_platform_helper_version,
    cli_demodjango_branch,
    expected_demodjango_branch,
    expected_pinned_version,
    module_source_override,
    platform_config_for_env_pipelines,
):

    app_name = "test-app"

    if is_auto:
        platform_config_for_env_pipelines["default_versions"] = {"platform-helper": "auto"}
    else:
        platform_config_for_env_pipelines["default_versions"] = {
            "platform-helper": expected_platform_helper_version
        }

    fakefs.create_file(PLATFORM_CONFIG_FILE, contents=yaml.dump(platform_config_for_env_pipelines))

    mocks = PipelineMocks(app_name)

    if use_environment_variable_platform_helper_version:
        mocks.mock_platform_helper_versioning.platform_helper_version_override = None
    else:
        mocks.mock_platform_helper_versioning.platform_helper_version_override = (
            expected_platform_helper_version
        )

    mocks.mock_platform_helper_versioning.environment_variable_provider[
        PLATFORM_HELPER_VERSION_OVERRIDE_KEY
    ] = expected_platform_helper_version
    mocks.mock_platform_helper_versioning.environment_variable_provider[
        TERRAFORM_ENVIRONMENT_PIPELINES_MODULE_SOURCE_OVERRIDE_ENV_VAR
    ] = module_source_override

    pipelines = Pipelines(**mocks.params())

    pipelines.generate(cli_demodjango_branch)

    expected_messages = [
        "File terraform/environment-pipelines/platform-sandbox-test/main.tf created",
        "File terraform/environment-pipelines/platform-prod-test/main.tf created",
    ]

    called_messages = [call_obj.args[0] for call_obj in pipelines.io.info.call_args_list]

    assert sorted(called_messages) == sorted(expected_messages)

    assert_terraform(
        app_name,
        "platform-sandbox-test",
        expected_platform_helper_version,
        expected_demodjango_branch,
        expected_pinned_version,
        module_source_override,
        "1111111111",
    )
    assert_terraform(
        app_name,
        "platform-prod-test",
        expected_platform_helper_version,
        expected_demodjango_branch,
        expected_pinned_version,
        module_source_override,
        "3333333333",
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
    platform_config_for_env_pipelines["default_versions"] = {"platform-helper": "14.0.0"}
    fakefs.create_file(PLATFORM_CONFIG_FILE, contents=yaml.dump(platform_config_for_env_pipelines))
    mocks = PipelineMocks(app_name)
    pipelines = Pipelines(**mocks.params())

    pipelines.generate("a-branch")

    expected_files_dir = Path(f"terraform/environment-pipelines/platform-prod-test/main.tf")
    assert expected_files_dir.exists()
    content = expected_files_dir.read_text()

    warn_calls = [call.args[0] for call in mocks.io.warn.mock_calls]
    assert (
        "No `deploy_repository` key set in platform-config.yml, this will become a required key. See full platform config reference in the docs: https://platform.readme.trade.gov.uk/reference/platform-config-yml/#core-configuration"
        in warn_calls
    )

    assert re.search(r'repository += +"uktrade/test-app-deploy"', content)


@pytest.mark.parametrize(
    "use_environment_variable_platform_helper_version, expected_platform_helper_version, module_source",
    [
        (
            False,
            "14.0.0",
            "git::git@github.com:uktrade/platform-tools.git//terraform/codebase-pipelines?depth=1&ref=14.0.0",
        ),
        (True, "test-branch", "../local/path/"),
    ],
)
def test_pipeline_generate_calls_generate_codebase_pipeline_config_with_expected_platform_helper_version(
    use_environment_variable_platform_helper_version,
    expected_platform_helper_version,
    module_source,
    codebase_pipeline_config_for_1_pipeline_and_2_run_groups,
    fakefs,
):
    app_name = "test-app"
    fakefs.create_file(
        PLATFORM_CONFIG_FILE,
        contents=yaml.dump(codebase_pipeline_config_for_1_pipeline_and_2_run_groups),
    )

    mocks = PipelineMocks(app_name)
    mocks.mock_platform_helper_versioning.platform_helper_version_override = (
        expected_platform_helper_version
    )

    mocks.mock_platform_helper_versioning.environment_variable_provider[
        TERRAFORM_CODEBASE_PIPELINES_MODULE_SOURCE_OVERRIDE_ENV_VAR
    ] = module_source

    pipelines = Pipelines(**mocks.params())

    pipelines.generate(None)

    mock_t_m_p = mocks.mock_terraform_manifest_provider
    mock_t_m_p.generate_codebase_pipeline_config.assert_called_once_with(
        codebase_pipeline_config_for_1_pipeline_and_2_run_groups,
        expected_platform_helper_version,
        {},
        "uktrade/my-app-deploy",
        module_source,
        None,  # workspace
    )


@pytest.mark.parametrize(
    "expected_platform_helper_version, module_source",
    [
        (
            "14.0.0",
            "git::git@github.com:uktrade/platform-tools.git//terraform/codebase-pipelines?depth=1&ref=14.0.0",
        ),
        ("test-branch", "../local/path/"),
    ],
)
def test_pipeline_generate_calls_generate_codebase_pipeline_config_with_imports(
    expected_platform_helper_version,
    module_source,
    codebase_pipeline_config_for_2_pipelines_and_1_run_group,
    fakefs,
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

    mocks.mock_platform_helper_versioning.platform_helper_version_override = (
        expected_platform_helper_version
    )

    mocks.mock_platform_helper_versioning.environment_variable_provider[
        TERRAFORM_CODEBASE_PIPELINES_MODULE_SOURCE_OVERRIDE_ENV_VAR
    ] = module_source

    pipelines = Pipelines(**mocks.params())

    pipelines.generate(None)

    mock_t_m_p = mocks.mock_terraform_manifest_provider
    mock_t_m_p.generate_codebase_pipeline_config.assert_called_once_with(
        codebase_pipeline_config_for_2_pipelines_and_1_run_group,
        expected_platform_helper_version,
        {"test_codebase": "my-app/test_codebase", "test_codebase_2": "my-app/test_codebase_2"},
        "uktrade/my-app-deploy",
        module_source,
        None,  # workspace
    )


def assert_terraform(
    app_name,
    aws_account,
    expected_version,
    expected_branch,
    expected_pinned_version,
    module_source_override,
    deploy_account_id,
):
    expected_files_dir = Path(f"terraform/environment-pipelines/{aws_account}/main.tf")
    assert expected_files_dir.exists()
    content = expected_files_dir.read_text()

    assert "# WARNING: This is an autogenerated file, not for manual editing." in content
    assert "# Generated by platform-helper v0.1-TEST / 2024-10-28 12:00:00" in content
    assert f'profile                  = "{aws_account}"' in content
    assert re.search(r'repository += +"uktrade/test-app-weird-name-deploy"', content)

    with open(expected_files_dir, "r") as file:
        parsed_terraform = hcl2.load(file)

        environment_pipeline_module = parsed_terraform["module"][0]["environment-pipelines"]

        if module_source_override:
            assert environment_pipeline_module["source"] == module_source_override
        else:
            assert (
                environment_pipeline_module["source"]
                == f"git::git@github.com:uktrade/platform-tools.git//terraform/environment-pipelines?depth=1&ref={expected_version}"
            )

        assert environment_pipeline_module["application"] == app_name

        if expected_branch:
            assert environment_pipeline_module["branch"] == expected_branch
        else:
            assert environment_pipeline_module["branch"] == "${each.value.branch}"

        assert parsed_terraform["provider"][0]["aws"]["allowed_account_ids"] == [deploy_account_id]

        assert not parsed_terraform["provider"][0]["aws"].get("alias")
        assert environment_pipeline_module["pinned_version"] == expected_pinned_version
