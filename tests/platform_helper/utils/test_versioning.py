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
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.platform_helper_versioning import (
    PlatformHelperVersioning,
)
from dbt_platform_helper.providers.semantic_version import (
    IncompatibleMajorVersionException,
)
from dbt_platform_helper.providers.semantic_version import (
    IncompatibleMinorVersionException,
)
from dbt_platform_helper.providers.semantic_version import PlatformHelperVersionStatus
from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.providers.validation import ValidationException
from dbt_platform_helper.utils.versioning import PlatformHelperVersionNotFoundException
from dbt_platform_helper.utils.versioning import RequiredVersion
from dbt_platform_helper.utils.versioning import get_aws_versions
from dbt_platform_helper.utils.versioning import get_copilot_versions
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


# TODO move to PlatformHelperVersion provider tests
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package",
    new=Mock(return_value=False),
)
@patch("dbt_platform_helper.utils.versioning.get_platform_helper_version_status")
def test_check_platform_helper_version_skips_when_running_local_version(version_compatibility):
    PlatformHelperVersioning().check_if_needs_update()

    version_compatibility.assert_not_called()


# TODO move to RequiredVersion domain
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
@patch(
    "dbt_platform_helper.providers.platform_helper_versioning.running_as_installed_package",
    new=Mock(return_value=True),
)
def test_check_platform_helper_version_shows_warning_when_different_than_file_spec():
    mock_io_provider = Mock()
    mock_platform_helper_version_provider = Mock()
    mock_platform_helper_version_provider.get_status.return_value = PlatformHelperVersionStatus(
        local=SemanticVersion(1, 0, 1),
        deprecated_version_file=SemanticVersion(1, 0, 0),
    )
    required_version = RequiredVersion(
        io=mock_io_provider, platform_helper_versioning=mock_platform_helper_version_provider
    )

    required_version.check_platform_helper_version_mismatch()

    mock_io_provider.warn.assert_called_with(
        f"WARNING: You are running platform-helper v1.0.1 against v1.0.0 specified for the project.",
    )


# TODO move to RequiredVersion domain
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
@patch(
    "dbt_platform_helper.providers.platform_helper_versioning.running_as_installed_package",
    new=Mock(return_value=True),
)
def test_check_platform_helper_version_shows_no_warning_when_same_as_file_spec():
    mock_io_provider = Mock()
    mock_platform_helper_version_provider = Mock()
    mock_platform_helper_version_provider.get_status.return_value = PlatformHelperVersionStatus(
        local=SemanticVersion(1, 0, 1),
        deprecated_version_file=SemanticVersion(1, 0, 0),
    )
    required_version = RequiredVersion(
        io=mock_io_provider, platform_helper_versioning=mock_platform_helper_version_provider
    )

    required_version.check_platform_helper_version_mismatch()

    mock_io_provider.warn.assert_not_called
    mock_io_provider.error.assert_not_called


# TODO move to RequiredVersion domain tests.  consolidate running_as_installed_package
@patch(
    "dbt_platform_helper.providers.platform_helper_versioning.running_as_installed_package",
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
        platform_helper_versioning=mock_platform_helper_version_provider, io=mock_io_provider
    )

    required_version.check_platform_helper_version_mismatch()

    mock_io_provider.warn.assert_called_with(
        f"WARNING: You are running platform-helper v1.0.1 against v1.0.0 specified for the project.",
    )


# TODO move to PlatformHelperVersion provider tests and ensure it's testing the right thing
# right now this always passes because the specific mock is never called
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package",
    new=Mock(return_value=True),
)
@patch("dbt_platform_helper.utils.versioning.get_platform_helper_version_status")
def test_check_platform_helper_version_skips_when_skip_environment_variable_is_set(
    version_compatibility,
):
    os.environ["PLATFORM_TOOLS_SKIP_VERSION_CHECK"] = "true"

    PlatformHelperVersioning().check_if_needs_update()

    version_compatibility.assert_not_called()


@pytest.mark.parametrize(
    "version_in_phv_file, version_in_platform_config, expected_warnings",
    (
        (
            True,
            False,
            [
                f"Please delete '{PLATFORM_HELPER_VERSION_FILE}' as it is now deprecated.",
                f"Create a section in the root of '{PLATFORM_CONFIG_FILE}':\n\ndefault_versions:\n  platform-helper: 3.3.3\n",
            ],
        ),
        (
            False,
            True,
            None,
        ),
        (
            True,
            True,
            [f"Please delete '{PLATFORM_HELPER_VERSION_FILE}' as it is now deprecated."],
        ),
    ),
)
# TODO add coverage for the include_project_versions parameter in the PlatformHelperVersion tests
# @pytest.mark.parametrize("include_project_versions", [False, True])
@patch("requests.get")
@patch("dbt_platform_helper.providers.version.version")
def test_platform_helper_version_deprecation_warnings(
    mock_version,
    mock_get,
    fakefs,
    version_in_phv_file,
    version_in_platform_config,
    expected_warnings,
):
    mock_version.return_value = "1.2.3"
    mock_get.return_value.json.return_value = {
        "releases": {"1.2.3": None, "2.3.4": None, "0.1.0": None}
    }
    platform_config = {"application": "my-app"}
    if version_in_platform_config:
        platform_config["default_versions"] = {"platform-helper": "2.2.2"}

    fakefs.create_file(PLATFORM_CONFIG_FILE, contents=yaml.dump(platform_config))

    if version_in_phv_file:
        fakefs.create_file(PLATFORM_HELPER_VERSION_FILE, contents="3.3.3")

    mock_io_provider = Mock()

    RequiredVersion(io=mock_io_provider).get_required_version()

    if expected_warnings:
        mock_io_provider.process_messages.assert_called_with(
            {"warnings": expected_warnings, "errors": []}
        )
    else:
        mock_io_provider.process_messages.assert_called_with({})


# TODO move to RequiredVersion domain tests
# TODO mock config provider instead of fs
@patch("requests.get")
@patch("dbt_platform_helper.providers.version.version")
def test_get_required_version_errors_if_version_is_not_specified(
    mock_version,
    mock_get,
    fakefs,
):
    mock_version.return_value = "1.2.3"
    mock_get.return_value.json.return_value = {
        "releases": {"1.2.3": None, "2.3.4": None, "0.1.0": None}
    }

    platform_config_without_default_version = {"application": "my-app"}
    fakefs.create_file(
        PLATFORM_CONFIG_FILE, contents=yaml.dump(platform_config_without_default_version)
    )

    mock_io_provider = Mock()

    print("provider mock", mock_io_provider)

    expected_message = f"""Cannot get dbt-platform-helper version from '{PLATFORM_CONFIG_FILE}'.
Create a section in the root of '{PLATFORM_CONFIG_FILE}':\n\ndefault_versions:\n  platform-helper: 1.2.3
"""

    with pytest.raises(PlatformHelperVersionNotFoundException):
        RequiredVersion(io=mock_io_provider).get_required_version()

    mock_io_provider.process_messages.assert_called_with(
        {"warnings": [], "errors": [expected_message]}
    )


# TODO Relocate when we refactor config command in DBTP-1538
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


# TODO Relocate when we refactor config command in DBTP-1538
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


# TODO this is testing both get_required_platform_helper_version and
# get_platform_helper_version_status.  We should instead unit test
# PlatformHelperVersion.get_status thoroughly and then inject VersionStatus for this test.
@pytest.mark.parametrize(
    "platform_helper_version_file_version,platform_config_default_version,expected_version",
    [
        ("0.0.1", None, "0.0.1"),
        ("0.0.1", "1.0.0", "1.0.0"),
    ],
)
@patch("dbt_platform_helper.providers.version.version", return_value="0.0.0")
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

    version_status = PlatformHelperVersioning().get_status()
    required_version = RequiredVersion()

    result = required_version.get_required_platform_helper_version(version_status=version_status)

    assert result == expected_version


# TODO this is testing both get_required_platform_helper_version and
# get_platform_helper_version_status.  We should instead unit test
# PlatformHelperVersion.get_status thoroughly and then inject VersionStatus for this test.
@pytest.mark.parametrize(
    "platform_helper_version_file_version, platform_config_default_version, pipeline_override, expected_version",
    [
        ("0.0.1", None, None, "0.0.1"),
        ("0.0.1", "1.0.0", None, "1.0.0"),
        (None, "3.0.0", "4.0.0", "4.0.0"),
        ("0.0.1", "4.0.0", "5.0.0", "5.0.0"),
    ],
)
@patch("dbt_platform_helper.providers.version.version", return_value="0.0.0")
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

    version_status = PlatformHelperVersioning().get_status()
    required_version = RequiredVersion()

    result = required_version.get_required_platform_helper_version(
        "main", version_status=version_status
    )

    assert result == expected_version


#
# TODO All the following tests still need to be reviewed....
#
@patch("click.secho")
@patch("dbt_platform_helper.providers.version.version", return_value="0.0.0")
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

    version_status = PlatformHelperVersioning().get_status()

    ClickIOProvider().process_messages(version_status.validate())
    with pytest.raises(PlatformException):
        required_version.get_required_platform_helper_version("main", version_status=version_status)

    secho.assert_called_with(
        f"""Error: Cannot get dbt-platform-helper version from '{PLATFORM_CONFIG_FILE}'.
Create a section in the root of '{PLATFORM_CONFIG_FILE}':\n\ndefault_versions:\n  platform-helper: 1.2.3
""",
        fg="red",
    )


@patch("click.secho")
@patch("dbt_platform_helper.providers.version.version", return_value="0.0.0")
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
        "bogus_pipeline", version_status=PlatformHelperVersioning().get_status()
    )

    assert result == default_version


# TODO move to RequiredVersion domain tests
# TODO use as template to recreate PlatformHelperVersion test cases for PlatformHelperVersion unit tests
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
            "bogus_pipeline", version_status=PlatformHelperVersioning().get_status()
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
            "main", version_status=PlatformHelperVersioning().get_status()
        )

        assert result == pipeline_override_version
