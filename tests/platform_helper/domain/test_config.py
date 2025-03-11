import webbrowser
from unittest import mock
from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import call

import pytest
from prettytable import PrettyTable

from dbt_platform_helper.domain.config import Config
from dbt_platform_helper.domain.config import NoDeploymentRepoConfigException
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.semantic_version import PlatformHelperVersionStatus
from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.providers.semantic_version import VersionStatus

yes = "\033[92m✔\033[0m"
no = "\033[91m✖\033[0m"
maybe = "\033[93m?\033[0m"


class ConfigMocks:
    def __init__(self, *args, **kwargs):
        self.io = kwargs.get("io", Mock(spec=ClickIOProvider))
        self.platform_helper_versioning_domain = kwargs.get(
            "platform_helper_versioning_domain", MagicMock(spec=PlatformHelperVersioning)
        )
        self.platform_helper_version_status = kwargs.get(
            "platform_helper_version_status",
            (PlatformHelperVersionStatus(SemanticVersion(1, 0, 0), SemanticVersion(1, 0, 0))),
        )
        self.platform_helper_versioning_domain._get_version_status.return_value = (
            self.platform_helper_version_status
        )

        self.sso = kwargs.get("sso", Mock())
        self.sso_oidc = kwargs.get("sso_oidc", Mock())

        self.aws_version = kwargs.get(
            "aws_version", VersionStatus(SemanticVersion(1, 0, 0), SemanticVersion(1, 0, 0))
        )
        self.copilot_version = kwargs.get(
            "copilot_version", VersionStatus(SemanticVersion(1, 0, 0), SemanticVersion(1, 0, 0))
        )
        self.get_aws_versions = kwargs.get("get_aws_versions", Mock(return_value=self.aws_version))
        self.get_copilot_versions = kwargs.get(
            "get_copilot_versions", Mock(return_value=self.copilot_version)
        )

    def params(self):
        return {
            "io": self.io,
            "sso": self.sso,
            "sso_oidc": self.sso_oidc,
            "platform_helper_versioning_domain": self.platform_helper_versioning_domain,
            "get_aws_versions": self.get_aws_versions,
            "get_copilot_versions": self.get_copilot_versions,
            # "get_template_generated_with_version": self.get_template_generated_with_version,
            # "validate_template_version": self.validate_template_version,
        }


class TestConfigValidate:

    def test_validate(self, fakefs):
        fakefs.create_file(
            "platform-config.yml",
            # TODO add in default version and test
            # contents="default_versions:\n  platform-helper: 1.0.0"
        )
        fakefs.create_file(
            "/copilot/environments/dev/addons/test_addon.yml",
            contents="# Generated by platform-helper v1.0.0",
        )

        config_mocks = ConfigMocks()
        config_domain = Config(**config_mocks.params())

        with pytest.raises(SystemExit) as excinfo:
            config_domain.validate()
        assert excinfo.value.code == 0

        config_mocks.io.debug.assert_has_calls(
            [
                call("\nDetected a deployment repository\n"),
                call("Checking tooling versions..."),
                call("Checking addons templates versions..."),
            ]
        )

        for call_args in config_mocks.io.info.call_args_list:
            print(repr(call_args))

        yes = "\033[92m✔\033[0m"
        no = "\033[91m✖\033[0m"
        expected_tool_version_table = PrettyTable()
        expected_tool_version_table.field_names = [
            "Tool",
            "Local version",
            "Released version",
            "Running latest?",
        ]
        expected_tool_version_table.align["Tool"] = "l"
        expected_tool_version_table.add_row(
            [
                "aws",
                "1.0.0",
                "1.0.0",
                yes,
            ]
        )
        expected_tool_version_table.add_row(
            [
                "copilot",
                "1.0.0",
                "1.0.0",
                yes,
            ]
        )
        expected_tool_version_table.add_row(
            [
                "dbt-platform-helper",
                "1.0.0",
                "1.0.0",
                yes,
            ]
        )

        expected_addon_table = PrettyTable()
        expected_addon_table.field_names = [
            "Addons Template File",
            "Generated with",
            "Compatible with local?",
            "Compatible with latest?",
        ]
        expected_addon_table.align["Addons Template File"] = "l"
        expected_addon_table.add_row(
            [
                "copilot/environments/dev/addons/test_addon.yml",
                "1.0.0",
                yes,
                yes,
            ]
        )

        assert repr(config_mocks.io.info.call_args_list[0][0][0]) == repr(
            expected_tool_version_table
        )
        assert repr(config_mocks.io.info.call_args_list[1][0][0]) == repr(expected_addon_table)
        config_mocks.io.info.assert_has_calls(
            [
                call(
                    ANY,  # tested above due to PrettyTable being difficult to compare
                ),
                call(
                    ANY,  # tested above due to PrettyTable being difficult to compare
                ),
            ],
        )

        config_mocks.platform_helper_versioning_domain._get_version_status.assert_called_with(
            include_project_versions=True
        )

        config_mocks.io.process_messages.assert_called_with(
            {
                "warnings": [],
                "errors": [
                    "Cannot get dbt-platform-helper version from 'platform-config.yml'.\nCreate a section in the root of 'platform-config.yml':\n\ndefault_versions:\n  platform-helper: 1.0.0\n"
                ],
            }
        )
        config_mocks.get_aws_versions.assert_called()
        config_mocks.get_copilot_versions.assert_called()

    def test_validate_not_installed(self, fakefs):
        fakefs.create_file("platform-config.yml")
        fakefs.create_file(
            "/copilot/environments/dev/addons/test_addon.yml",
            contents="",
        )

        config_mocks = ConfigMocks(
            aws_version=VersionStatus(None, SemanticVersion(2, 0, 0)),
            copilot_version=VersionStatus(None, SemanticVersion(3, 0, 0)),
        )

        print(config_mocks.copilot_version.installed)
        config_domain = Config(**config_mocks.params())

        with pytest.raises(SystemExit) as excinfo:
            config_domain.validate()

        assert excinfo.value.code == 1

        for call_args in config_mocks.io.info.call_args_list:
            print(repr(call_args))

        config_mocks.io.debug.assert_has_calls(
            [
                call("\nDetected a deployment repository\n"),
                call("Checking tooling versions..."),
                call("Checking addons templates versions..."),
            ]
        )

        yes = "\033[92m✔\033[0m"
        no = "\033[91m✖\033[0m"
        expected_tool_version_table = PrettyTable()
        expected_tool_version_table.field_names = [
            "Tool",
            "Local version",
            "Released version",
            "Running latest?",
        ]
        expected_tool_version_table.align["Tool"] = "l"
        expected_tool_version_table.add_row(
            [
                "aws",
                None,
                "2.0.0",
                no,
            ]
        )
        expected_tool_version_table.add_row(
            [
                "copilot",
                None,
                "3.0.0",
                no,
            ]
        )
        expected_tool_version_table.add_row(
            [
                "dbt-platform-helper",
                "1.0.0",
                "1.0.0",
                yes,
            ]
        )
        expected_addon_table = PrettyTable()
        expected_addon_table.field_names = [
            "Addons Template File",
            "Generated with",
            "Compatible with local?",
            "Compatible with latest?",
        ]
        expected_addon_table.align["Addons Template File"] = "l"
        expected_addon_table.add_row(
            [
                "copilot/environments/dev/addons/test_addon.yml",
                maybe,
                maybe,
                maybe,
            ]
        )

        assert repr(config_mocks.io.info.call_args_list[0][0][0]) == repr(
            expected_tool_version_table
        )
        assert repr(config_mocks.io.info.call_args_list[5][0][0]) == repr(expected_addon_table)
        config_mocks.io.info.assert_has_calls(
            [
                call(
                    ANY,  # tested above due to PrettyTable being difficult to compare
                ),
                call("\nRecommendations:\n"),
                call("  - Install AWS Copilot https://aws.github.io/copilot-cli/"),
                call("  - Install AWS CLI https://aws.amazon.com/cli/"),
                call(""),
                call(
                    ANY,  # tested above due to PrettyTable being difficult to compare
                ),
                call("\nRecommendations:\n"),
                call(
                    "  - Upgrade dbt-platform-helper to version 1.0.0 `pip install --upgrade dbt-platform-helper==1.0.0`."
                ),
                call(
                    "    Post upgrade, run `platform-helper copilot make-addons` to update your addon templates."
                ),
                call(""),
            ],
        )

        config_mocks.platform_helper_versioning_domain._get_version_status.assert_called_with(
            include_project_versions=True
        )

        config_mocks.io.process_messages.assert_called_with(
            {
                "warnings": [],
                "errors": [
                    "Cannot get dbt-platform-helper version from 'platform-config.yml'.\nCreate a section in the root of 'platform-config.yml':\n\ndefault_versions:\n  platform-helper: 1.0.0\n"
                ],
            }
        )
        config_mocks.get_aws_versions.assert_called()
        config_mocks.get_copilot_versions.assert_called()

    def test_validate_outdated(self, fakefs):
        fakefs.create_file("platform-config.yml")
        fakefs.create_file(
            "/copilot/environments/dev/addons/test_addon.yml",
            contents="# Generated by platform-helper v0.1.0",
        )

        config_mocks = ConfigMocks(
            platform_helper_version_status=PlatformHelperVersionStatus(
                SemanticVersion(1, 0, 0), SemanticVersion(2, 0, 0)
            ),
            aws_version=VersionStatus(SemanticVersion(0, 2, 0), SemanticVersion(2, 0, 0)),
            copilot_version=VersionStatus(SemanticVersion(0, 3, 0), SemanticVersion(3, 0, 0)),
        )
        config_domain = Config(**config_mocks.params())

        with pytest.raises(SystemExit) as excinfo:
            config_domain.validate()

        assert excinfo.value.code == 1

        for call_args in config_mocks.io.info.call_args_list:
            print(repr(call_args))

        config_mocks.io.debug.assert_has_calls(
            [
                call("\nDetected a deployment repository\n"),
                call("Checking tooling versions..."),
                call("Checking addons templates versions..."),
            ]
        )

        yes = "\033[92m✔\033[0m"
        no = "\033[91m✖\033[0m"
        expected_tool_version_table = PrettyTable()
        expected_tool_version_table.field_names = [
            "Tool",
            "Local version",
            "Released version",
            "Running latest?",
        ]
        expected_tool_version_table.align["Tool"] = "l"
        expected_tool_version_table.add_row(
            [
                "aws",
                "0.2.0",
                "2.0.0",
                no,
            ]
        )
        expected_tool_version_table.add_row(
            [
                "copilot",
                "0.3.0",
                "3.0.0",
                no,
            ]
        )
        expected_tool_version_table.add_row(
            [
                "dbt-platform-helper",
                "1.0.0",
                "2.0.0",
                no,
            ]
        )

        expected_addon_table = PrettyTable()
        expected_addon_table.field_names = [
            "Addons Template File",
            "Generated with",
            "Compatible with local?",
            "Compatible with latest?",
        ]
        expected_addon_table.align["Addons Template File"] = "l"
        expected_addon_table.add_row(
            [
                "copilot/environments/dev/addons/test_addon.yml",
                "0.1.0",
                no,
                no,
            ]
        )

        assert repr(config_mocks.io.info.call_args_list[0][0][0]) == repr(
            expected_tool_version_table
        )
        assert repr(config_mocks.io.info.call_args_list[7][0][0]) == repr(expected_addon_table)
        config_mocks.io.info.assert_has_calls(
            [
                call(
                    ANY,  # tested above due to PrettyTable being difficult to compare
                ),
                call("\nRecommendations:\n"),
                call("  - Upgrade AWS CLI to version 2.0.0."),
                call("  - Upgrade AWS Copilot to version 3.0.0."),
                call(
                    "  - Upgrade dbt-platform-helper to version 2.0.0 `pip install --upgrade dbt-platform-helper==2.0.0`."
                ),
                call(
                    "    Post upgrade, run `platform-helper copilot make-addons` to update your addon templates."
                ),
                call(""),
                call(
                    ANY,  # tested above due to PrettyTable being difficult to compare
                ),
                call("\nRecommendations:\n"),
                call(
                    "  - Upgrade dbt-platform-helper to version 2.0.0 `pip install --upgrade dbt-platform-helper==2.0.0`."
                ),
                call(
                    "    Post upgrade, run `platform-helper copilot make-addons` to update your addon templates."
                ),
                call(""),
            ],
        )

        config_mocks.platform_helper_versioning_domain._get_version_status.assert_called_with(
            include_project_versions=True
        )

        config_mocks.io.process_messages.assert_called_with(
            {
                "warnings": [],
                "errors": [
                    "Cannot get dbt-platform-helper version from 'platform-config.yml'.\nCreate a section in the root of 'platform-config.yml':\n\ndefault_versions:\n  platform-helper: 1.0.0\n"
                ],
            }
        )
        config_mocks.get_aws_versions.assert_called()
        config_mocks.get_copilot_versions.assert_called()

    # TODO ensure expected behaviour
    def test_no_platform_config(self, fakefs, capfd):
        fakefs.create_file(
            "/copilot/environments/dev/addons/test_addon.yml",
            contents="# Generated by platform-helper v0.1.0",
        )

        config_mocks = ConfigMocks()
        config_domain = Config(**config_mocks.params())

        with pytest.raises(SystemExit) as excinfo:
            config_domain.validate()

        assert excinfo.value.code == 1
        assert (
            "Error: `platform-config.yml` is missing. Please check it exists and you are in the root directory of your deployment project."
            in capfd.readouterr().err
        )

        config_mocks.io.debug.assert_has_calls(
            [
                call("\nDetected a deployment repository\n"),
                call("Checking tooling versions..."),
            ]
        )
        config_mocks.platform_helper_versioning_domain._get_version_status.assert_called_with(
            include_project_versions=True
        )
        config_mocks.io.process_messages.assert_called_with(
            {
                "warnings": [],
                "errors": [
                    "Cannot get dbt-platform-helper version from 'platform-config.yml'.\nCreate a section in the root of 'platform-config.yml':\n\ndefault_versions:\n  platform-helper: 1.0.0\n"
                ],
            }
        )

    def test_no_copilot_repo(self, fakefs):
        config_domain = Config()
        with pytest.raises(
            NoDeploymentRepoConfigException,
            match="Could not find a deployment repository, no checks to run.",
        ):
            config_domain.validate()


class TestConfigGenerateAWS:
    @mock.patch.object(webbrowser, "open")
    def test_aws_with_default_file_path(self, mock_webbrowser):
        config_mocks = ConfigMocks()
        config_domain = Config(**config_mocks.params())

        # TODO: define interface for SSO OIDC Provider. Proposed:
        # register(client_name, client_type) -> client_id, client_secret ??
        # start_device_authorization(client_id, client_secret, start_url)
        # -> url, device_code

        config_mocks.sso_oidc.register.return_value = {
            "clientId": "TEST_CLIENT_ID",
            "clientSecret": "TEST_CLIENT_SECRET",
        }

        config_mocks.sso_oidc.start_device_authorization.return_value = {
            "verificationUriComplete": "TEST_VERIFICATION_URI_COMPLETE",
            "deviceCode": "TEST_DEVICE_CODE",
        }

        config_domain.generate_aws()
        config_mocks.sso_oidc.register.assert_called_with(
            client_name="platform-helper", client_type="public"
        )
        config_mocks.sso_oidc.start_device_authorization.assert_called_with(
            client_id="TEST_CLIENT_ID",
            client_secret="TEST_CLIENT_SECRET",
            start_url="https://uktrade.awsapps.com/start",
        )
