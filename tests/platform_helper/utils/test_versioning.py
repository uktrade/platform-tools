import os
from pathlib import Path
from typing import Tuple
from typing import Type
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import yaml

from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_FILE
from dbt_platform_helper.domain.platform_helper_version import PlatformHelperVersion
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.semantic_version import (
    IncompatibleMajorVersionException,
)
from dbt_platform_helper.providers.semantic_version import (
    IncompatibleMinorVersionException,
)
from dbt_platform_helper.providers.semantic_version import PlatformHelperVersionStatus
from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.providers.validation import ValidationException
from dbt_platform_helper.utils.versioning import RequiredVersion
from dbt_platform_helper.utils.versioning import get_aws_versions
from dbt_platform_helper.utils.versioning import get_copilot_versions
from dbt_platform_helper.utils.versioning import get_platform_helper_version_status
from dbt_platform_helper.utils.versioning import (
    get_required_terraform_platform_modules_version,
)
from dbt_platform_helper.utils.versioning import validate_template_version
from tests.platform_helper.conftest import FIXTURES_DIR


# TODO Relocate when we refactor config command in DBTP-1538
@pytest.mark.parametrize(
    "template_check",
    [
        ("addon_newer_major_version.yml", IncompatibleMajorVersionException, ""),
        ("addon_newer_minor_version.yml", IncompatibleMinorVersionException, ""),
        ("addon_older_major_version.yml", IncompatibleMajorVersionException, ""),
        ("addon_older_minor_version.yml", IncompatibleMinorVersionException, ""),
        ("addon_no_version.yml", ValidationException, "Template %s has no version information"),
    ],
)
def test_validate_template_version(template_check: Tuple[str, Type[BaseException], str]):
    template_name, raises, message = template_check

    with pytest.raises(raises) as exception:
        template_path = str(Path(f"{FIXTURES_DIR}/version_validation/{template_name}").resolve())
        validate_template_version(SemanticVersion(10, 10, 10), template_path)

    if message:
        assert (message % template_path) == str(exception.value)


@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package",
    new=Mock(return_value=False),
)
@patch("dbt_platform_helper.utils.versioning.get_platform_helper_version_status")
def test_check_platform_helper_version_skips_when_running_local_version(version_compatibility):
    PlatformHelperVersion().check_if_needs_update()

    version_compatibility.assert_not_called()


@patch("click.secho")
@patch("dbt_platform_helper.utils.versioning.get_platform_helper_version_status")
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
def test_check_platform_helper_version_shows_warning_when_different_than_file_spec(
    get_file_app_versions, secho
):
    get_file_app_versions.return_value = PlatformHelperVersionStatus(
        local=SemanticVersion(1, 0, 1),
        deprecated_version_file=SemanticVersion(1, 0, 0),
    )

    required_version = RequiredVersion()

    required_version.check_platform_helper_version_mismatch()

    secho.assert_called_with(
        f"WARNING: You are running platform-helper v1.0.1 against v1.0.0 specified for the project.",
        fg="magenta",
    )


@patch("dbt_platform_helper.utils.versioning.running_as_installed_package")
@patch("click.secho")
@patch("dbt_platform_helper.utils.versioning.get_platform_helper_version_status")
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
def test_check_platform_helper_version_shows_warning_when_different_than_file_spec(
    get_file_app_versions, secho, mock_running_as_installed_package
):
    get_file_app_versions.return_value = PlatformHelperVersionStatus(
        local=SemanticVersion(1, 0, 1),
        deprecated_version_file=SemanticVersion(1, 0, 0),
    )
    mock_running_as_installed_package.return_value = False

    required_version = RequiredVersion()

    required_version.check_platform_helper_version_mismatch()

    secho.assert_not_called()


# TODO move to domain tests.  consolidate running_as_installed_package
@patch(
    "dbt_platform_helper.domain.platform_helper_version.running_as_installed_package",
    new=Mock(return_value=True),
)
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
def test_check_platform_helper_version_does_not_fall_over_if_platform_helper_version_file_not_present():
    mock_platform_helper_version_provider = Mock()
    mock_platform_helper_version_provider.get_status.return_value = PlatformHelperVersionStatus(
        local=SemanticVersion(1, 0, 1),
        deprecated_version_file=None,
        platform_config_default=SemanticVersion(1, 0, 0),
    )

    mock_io_provider = Mock()

    required_version = RequiredVersion(
        platform_helper_version_provider=mock_platform_helper_version_provider, io=mock_io_provider
    )

    required_version.check_platform_helper_version_mismatch()

    mock_io_provider.warn.assert_called_with(
        f"WARNING: You are running platform-helper v1.0.1 against v1.0.0 specified for the project.",
    )


@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package",
    new=Mock(return_value=True),
)
@patch("dbt_platform_helper.utils.versioning.get_platform_helper_version_status")
def test_check_platform_helper_version_skips_when_skip_environment_variable_is_set(
    version_compatibility,
):
    os.environ["PLATFORM_TOOLS_SKIP_VERSION_CHECK"] = "true"

    PlatformHelperVersion().check_if_needs_update()

    version_compatibility.assert_not_called()


@patch("requests.get")
@patch("dbt_platform_helper.domain.platform_helper_version.version")
def test_get_platform_helper_version_status(mock_version, mock_get, fakefs, valid_platform_config):
    mock_version.return_value = "1.1.1"
    mock_get.return_value.json.return_value = {
        "releases": {"1.2.3": None, "2.3.4": None, "0.1.0": None}
    }
    fakefs.create_file(PLATFORM_HELPER_VERSION_FILE, contents="5.6.7")
    config = valid_platform_config
    fakefs.create_file(PLATFORM_CONFIG_FILE, contents=yaml.dump(config))

    version_status = PlatformHelperVersion().get_status()

    assert version_status.local == SemanticVersion(1, 1, 1)
    assert version_status.latest == SemanticVersion(2, 3, 4)
    assert version_status.deprecated_version_file == SemanticVersion(5, 6, 7)
    assert version_status.platform_config_default == SemanticVersion(10, 2, 0)
    assert version_status.pipeline_overrides == {"test": "main", "prod-main": "9.0.9"}


@patch("requests.get")
@patch("dbt_platform_helper.domain.platform_helper_version.version")
def test_get_platform_helper_version_status_with_invalid_yaml_in_platform_config(
    mock_local_version, mock_latest_release_request, fakefs
):
    mock_local_version.return_value = "1.1.1"
    mock_latest_release_request.return_value.json.return_value = {
        "releases": {"1.2.3": None, "2.3.4": None, "0.1.0": None}
    }
    fakefs.create_file(PLATFORM_HELPER_VERSION_FILE, contents="5.6.7")
    fakefs.create_file(PLATFORM_CONFIG_FILE, contents="{")

    version_status = get_platform_helper_version_status()

    assert version_status.local == SemanticVersion(1, 1, 1)
    assert version_status.latest == SemanticVersion(2, 3, 4)
    assert version_status.deprecated_version_file == SemanticVersion(5, 6, 7)
    assert version_status.platform_config_default == None
    assert version_status.pipeline_overrides == {}


@patch("requests.get")
@patch("dbt_platform_helper.domain.platform_helper_version.version")
def test_get_platform_helper_version_status_with_invalid_config(
    mock_version,
    mock_get,
    fakefs,
    create_invalid_platform_config_file,
):
    mock_version.return_value = "1.1.1"
    mock_get.return_value.json.return_value = {
        "releases": {"1.2.3": None, "2.3.4": None, "0.1.0": None}
    }
    fakefs.create_file(PLATFORM_HELPER_VERSION_FILE, contents="5.6.7")

    version_status = get_platform_helper_version_status()

    assert version_status.local == SemanticVersion(1, 1, 1)
    assert version_status.latest == SemanticVersion(2, 3, 4)
    assert version_status.deprecated_version_file == SemanticVersion(5, 6, 7)
    assert version_status.platform_config_default == SemanticVersion(1, 2, 3)
    assert version_status.pipeline_overrides == {"prod-main": "9.0.9"}


# @pytest.mark.parametrize(
#     "version_in_phv_file, version_in_platform_config, expected_message, message_colour",
#     (
#         (
#             False,
#             False,
#             f"Error: Cannot get dbt-platform-helper version from '{PLATFORM_CONFIG_FILE}'.\n"
#             f"Create a section in the root of '{PLATFORM_CONFIG_FILE}':\n\ndefault_versions:\n  platform-helper: 1.2.3\n",
#             "red",
#         ),
#         (
#             True,
#             False,
#             f"Please delete '{PLATFORM_HELPER_VERSION_FILE}' as it is now deprecated.\n"
#             f"Create a section in the root of '{PLATFORM_CONFIG_FILE}':\n\ndefault_versions:\n"
#             "  platform-helper: 3.3.3\n",
#             "magenta",
#         ),
#         (False, True, None, "magenta"),
#         (
#             True,
#             True,
#             f"Please delete '{PLATFORM_HELPER_VERSION_FILE}' as it is now deprecated.",
#             "magenta",
#         ),
#     ),
# )
# @pytest.mark.parametrize("include_project_versions", [False, True])
# @patch("click.secho")
# @patch("requests.get")
# @patch("dbt_platform_helper.utils.versioning.version")
# def test_platform_helper_version_warnings(
#     mock_version,
#     mock_get,
#     secho,
#     fakefs,
#     version_in_phv_file,
#     version_in_platform_config,
#     expected_message,
#     message_colour,
#     include_project_versions,
# ):
#     mock_version.return_value = "1.2.3"
#     mock_get.return_value.json.return_value = {
#         "releases": {"1.2.3": None, "2.3.4": None, "0.1.0": None}
#     }
#     platform_config = {"application": "my-app"}
#     if version_in_platform_config:
#         platform_config["default_versions"] = {"platform-helper": "2.2.2"}
#     fakefs.create_file(PLATFORM_CONFIG_FILE, contents=yaml.dump(platform_config))

#     if version_in_phv_file:
#         fakefs.create_file(PLATFORM_HELPER_VERSION_FILE, contents="3.3.3")

#     get_platform_helper_version_status(include_project_versions=include_project_versions)

#     if expected_message and include_project_versions:
#         secho.assert_called_with(expected_message, fg=message_colour)
#     else:
#         secho.assert_not_called()


@patch("subprocess.run")
@patch(
    "dbt_platform_helper.providers.version.GithubVersionProvider.get_latest_version",
    return_value=SemanticVersion(2, 0, 0),
)
def test_get_copilot_versions(mock_get_github_released_version, mock_run):
    mock_run.return_value.stdout = b"1.0.0"

    versions = get_copilot_versions()

    assert versions.local == SemanticVersion(1, 0, 0)
    assert versions.latest == SemanticVersion(2, 0, 0)


@patch("subprocess.run")
@patch(
    "dbt_platform_helper.providers.version.GithubVersionProvider.get_latest_version",
    return_value=SemanticVersion(2, 0, 0),
)
def test_get_aws_versions(mock_get_github_released_version, mock_run):
    mock_run.return_value.stdout = b"aws-cli/1.0.0"
    versions = get_aws_versions()

    assert versions.local == SemanticVersion(1, 0, 0)
    assert versions.latest == SemanticVersion(2, 0, 0)


@pytest.mark.parametrize(
    "platform_helper_version_file_version,platform_config_default_version,expected_version",
    [
        ("0.0.1", None, "0.0.1"),
        ("0.0.1", "1.0.0", "1.0.0"),
    ],
)
@patch("dbt_platform_helper.domain.platform_helper_version.version", return_value="0.0.0")
@patch("requests.get")
def test_get_required_platform_helper_version(
    mock_get,
    mock_version,
    fakefs,
    platform_helper_version_file_version,
    platform_config_default_version,
    expected_version,
):
    mock_get.return_value.json.return_value = {
        "releases": {"1.2.3": None, "2.3.4": None, "0.1.0": None}
    }
    if platform_helper_version_file_version:
        Path(PLATFORM_HELPER_VERSION_FILE).write_text("0.0.1")

    platform_config = {
        "application": "my-app",
        "environments": {"dev": None},
        "environment_pipelines": {
            "main": {"slack_channel": "abc", "trigger_on_push": True, "environments": {"dev": None}}
        },
    }
    if platform_config_default_version:
        platform_config["default_versions"] = {"platform-helper": platform_config_default_version}

    Path(PLATFORM_CONFIG_FILE).write_text(yaml.dump(platform_config))

    required_version = RequiredVersion()

    result = required_version.get_required_platform_helper_version(
        version_status=get_platform_helper_version_status()
    )

    assert result == expected_version


@pytest.mark.parametrize(
    "platform_helper_version_file_version, platform_config_default_version, pipeline_override, expected_version",
    [
        ("0.0.1", None, None, "0.0.1"),
        ("0.0.1", "1.0.0", None, "1.0.0"),
        (None, "3.0.0", "4.0.0", "4.0.0"),
        ("0.0.1", "4.0.0", "5.0.0", "5.0.0"),
    ],
)
@patch("dbt_platform_helper.domain.platform_helper_version.version", return_value="0.0.0")
@patch("requests.get")
def test_get_required_platform_helper_version_in_pipeline(
    mock_get,
    mock_version,
    fakefs,
    platform_helper_version_file_version,
    platform_config_default_version,
    pipeline_override,
    expected_version,
):
    mock_get.return_value.json.return_value = {
        "releases": {"1.2.3": None, "2.3.4": None, "0.1.0": None}
    }
    if platform_helper_version_file_version:
        Path(PLATFORM_HELPER_VERSION_FILE).write_text("0.0.1")

    platform_config = {
        "application": "my-app",
        "environments": {"dev": None},
        "environment_pipelines": {
            "main": {"slack_channel": "abc", "trigger_on_push": True, "environments": {"dev": None}}
        },
    }
    if platform_config_default_version:
        platform_config["default_versions"] = {"platform-helper": platform_config_default_version}

    if pipeline_override:
        platform_config["environment_pipelines"]["main"]["versions"] = {
            "platform-helper": pipeline_override
        }

    Path(PLATFORM_CONFIG_FILE).write_text(yaml.dump(platform_config))

    required_version = RequiredVersion()

    result = required_version.get_required_platform_helper_version(
        "main", version_status=get_platform_helper_version_status()
    )

    assert result == expected_version


@patch("click.secho")
@patch("dbt_platform_helper.domain.platform_helper_version.version", return_value="0.0.0")
@patch("requests.get")
def test_get_required_platform_helper_version_errors_when_no_platform_config_version_available(
    mock_get,
    mock_version,
    secho,
    fakefs,
):
    mock_get.return_value.json.return_value = {
        "releases": {"1.2.3": None, "2.3.4": None, "0.1.0": None}
    }
    mock_version.return_value = "1.2.3"
    Path(PLATFORM_CONFIG_FILE).write_text(yaml.dump({"application": "my-app"}))
    # TODO need to inject the config provider instead of relying on FS
    required_version = RequiredVersion()
    version_status = get_platform_helper_version_status()

    ClickIOProvider().process_messages(version_status.warn())
    print("SRTATUS:", version_status)
    with pytest.raises(PlatformException):
        required_version.get_required_platform_helper_version("main", version_status=version_status)

    secho.assert_called_with(
        f"""Error: Cannot get dbt-platform-helper version from '{PLATFORM_CONFIG_FILE}'.
Create a section in the root of '{PLATFORM_CONFIG_FILE}':\n\ndefault_versions:\n  platform-helper: 1.2.3
""",
        fg="red",
    )


@patch("click.secho")
@patch("dbt_platform_helper.domain.platform_helper_version.version", return_value="0.0.0")
@patch("requests.get")
def test_get_required_platform_helper_version_does_not_call_external_services_if_versions_passed_in(
    mock_get,
    mock_version,
    secho,
):
    required_version = RequiredVersion()

    result = required_version.get_required_platform_helper_version(
        version_status=PlatformHelperVersionStatus(platform_config_default=SemanticVersion(1, 2, 3))
    )

    assert result == "1.2.3"
    mock_version.assert_not_called()
    mock_get.assert_not_called()


@pytest.mark.parametrize(
    "cli_terraform_platform_version, config_terraform_platform_version, expected_version",
    [
        ("feature_branch", "5", "feature_branch"),
        (None, "5", "5"),
        (None, None, DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION),
    ],
)
def test_determine_terraform_platform_modules_version(
    cli_terraform_platform_version, config_terraform_platform_version, expected_version
):
    assert (
        get_required_terraform_platform_modules_version(
            cli_terraform_platform_version, config_terraform_platform_version
        )
        == expected_version
    )


@patch(
    "dbt_platform_helper.providers.version.PyPiVersionProvider.get_latest_version",
    return_value="10.9.9",
)
def test_fall_back_on_default_if_pipeline_option_is_not_a_valid_pipeline(
    mock_latest_release, fakefs
):
    default_version = "1.2.3"
    platform_config = {
        "application": "my-app",
        "default_versions": {"platform-helper": default_version},
        "environments": {"dev": None},
        "environment_pipelines": {
            "main": {
                "versions": {"platform-helper": "1.1.1"},
                "slack_channel": "abc",
                "trigger_on_push": True,
                "environments": {"dev": None},
            }
        },
    }
    fakefs.create_file(Path(PLATFORM_CONFIG_FILE), contents=yaml.dump(platform_config))

    result = RequiredVersion().get_required_platform_helper_version(
        "bogus_pipeline", version_status=get_platform_helper_version_status()
    )

    assert result == default_version


@patch(
    "dbt_platform_helper.providers.version.PyPiVersionProvider.get_latest_version",
    return_value="10.9.9",
)
class TestVersionCommandWithInvalidConfig:
    DEFAULT_VERSION = "1.2.3"
    INVALID_CONFIG = {
        "default_versions": {"platform-helper": DEFAULT_VERSION},
        "a_bogus_field_that_invalidates_config": "foo",
    }

    def test_works_given_invalid_config(self, mock_latest_release, fakefs):
        default_version = "1.2.3"
        platform_config = self.INVALID_CONFIG
        fakefs.create_file(Path(PLATFORM_CONFIG_FILE), contents=yaml.dump(platform_config))

        result = RequiredVersion().get_required_platform_helper_version(
            "bogus_pipeline", version_status=get_platform_helper_version_status()
        )

        assert result == default_version

    def test_pipeline_override_given_invalid_config(self, mock_latest_release, fakefs):
        pipeline_override_version = "1.1.1"
        platform_config = self.INVALID_CONFIG
        platform_config["environment_pipelines"] = {
            "main": {
                "versions": {"platform-helper": pipeline_override_version},
            }
        }
        fakefs.create_file(Path(PLATFORM_CONFIG_FILE), contents=yaml.dump(platform_config))

        result = RequiredVersion().get_required_platform_helper_version(
            "main", version_status=get_platform_helper_version_status()
        )

        assert result == pipeline_override_version
