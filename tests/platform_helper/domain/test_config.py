import builtins
import os
import webbrowser
from unittest import mock
from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import call
from unittest.mock import mock_open

import pytest
from prettytable import PrettyTable

from dbt_platform_helper.domain.config import Config
from dbt_platform_helper.domain.config import NoDeploymentRepoConfigException
from dbt_platform_helper.domain.config import NoPlatformConfigException
from dbt_platform_helper.domain.versioning import AWSVersioning
from dbt_platform_helper.domain.versioning import CopilotVersioning
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.providers.aws.sso_auth import SSOAuthProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.providers.version_status import PlatformHelperVersionStatus
from dbt_platform_helper.providers.version_status import VersionStatus

START_URL = "https://uktrade.awsapps.com/start"

CLIENT_SECRET = "TEST_CLIENT_SECRET"

CLIENT_ID = "TEST_CLIENT_ID"

VERIFICATION_URI = "TEST_VERIFICATION_URI_COMPLETE"

yes = "\033[92m✔\033[0m"
no = "\033[91m✖\033[0m"
maybe = "\033[93m?\033[0m"


class ConfigMocks:
    def __init__(self, *args, **kwargs):
        self.io = kwargs.get("io", Mock(spec=ClickIOProvider))
        self.platform_helper_versioning = kwargs.get(
            "platform_helper_versioning", MagicMock(spec=PlatformHelperVersioning)
        )
        self.platform_helper_version_status = kwargs.get(
            "platform_helper_version_status",
            (PlatformHelperVersionStatus(SemanticVersion(1, 0, 0), SemanticVersion(1, 0, 0))),
        )
        self.platform_helper_versioning._get_version_status.return_value = (
            self.platform_helper_version_status
        )

        self.sso = kwargs.get("sso", Mock(spec=SSOAuthProvider))

        self.aws_version_status = kwargs.get(
            "aws_version_status", VersionStatus(SemanticVersion(1, 0, 0), SemanticVersion(1, 0, 0))
        )
        self.copilot_version_status = kwargs.get(
            "copilot_version_status",
            VersionStatus(SemanticVersion(1, 0, 0), SemanticVersion(1, 0, 0)),
        )
        self.aws_versioning = kwargs.get("aws_versioning", Mock(spec=AWSVersioning))
        self.aws_versioning.get_version_status.return_value = self.aws_version_status

        self.copilot_versioning = kwargs.get("copilot_versioning", Mock(spec=CopilotVersioning))
        self.copilot_versioning.get_version_status.return_value = self.copilot_version_status
        self.config_provider = kwargs.get("config_provider", Mock())
        self.migrator = kwargs.get("migrator", Mock())

    def params(self):
        return {
            "io": self.io,
            "sso": self.sso,
            "platform_helper_versioning": self.platform_helper_versioning,
            "aws_versioning": self.aws_versioning,
            "copilot_versioning": self.copilot_versioning,
            "config_provider": self.config_provider,
            "migrator": self.migrator,
        }


class TestConfigValidate:

    def test_validate(self, fakefs, create_valid_platform_config_file):
        fakefs.create_file(
            "/copilot/environments/dev/addons/test_addon.yml",
            contents="some other content # Generated by platform-helper v1.0.0 some more content",
        )

        config_mocks = ConfigMocks(
            platform_helper_version_status=PlatformHelperVersionStatus(
                SemanticVersion(1, 0, 0),
                SemanticVersion(1, 0, 0),
                platform_config_default=SemanticVersion(1, 0, 0),
            )
        )

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

        config_mocks.platform_helper_versioning._get_version_status.assert_called_with(
            include_project_versions=True
        )

        config_mocks.io.process_messages.assert_called_with({})
        config_mocks.aws_versioning.get_version_status.assert_called()
        config_mocks.copilot_versioning.get_version_status.assert_called()

    def test_validate_not_installed(self, fakefs):
        fakefs.create_file("platform-config.yml")
        fakefs.create_file(
            "/copilot/environments/dev/addons/test_addon.yml",
            contents="",
        )

        config_mocks = ConfigMocks(
            aws_version_status=VersionStatus(None, SemanticVersion(2, 0, 0)),
            copilot_version_status=VersionStatus(None, SemanticVersion(3, 0, 0)),
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
                call("\nRecommendations:\n", bold=True),
                call("  - Install AWS Copilot https://aws.github.io/copilot-cli/"),
                call("  - Install AWS CLI https://aws.amazon.com/cli/"),
                call(""),
                call(
                    ANY,  # tested above due to PrettyTable being difficult to compare
                ),
                call("\nRecommendations:\n", bold=True),
                call(
                    "  - Upgrade dbt-platform-helper to version 1.0.0 `pip install --upgrade dbt-platform-helper==1.0.0`."
                ),
                call(
                    "    Post upgrade, run `platform-helper copilot make-addons` to update your addon templates."
                ),
                call(""),
            ],
        )

        config_mocks.platform_helper_versioning._get_version_status.assert_called_with(
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
        config_mocks.aws_versioning.get_version_status.assert_called()
        config_mocks.copilot_versioning.get_version_status.assert_called()

    def test_validate_outdated(self, fakefs):
        fakefs.create_file("platform-config.yml")
        fakefs.create_file(
            "/copilot/environments/dev/addons/test_addon.yml",
            contents="some other content # Generated by platform-helper v0.1.0 some more content",
        )

        config_mocks = ConfigMocks(
            platform_helper_version_status=PlatformHelperVersionStatus(
                SemanticVersion(1, 0, 0), SemanticVersion(2, 0, 0)
            ),
            aws_version_status=VersionStatus(SemanticVersion(0, 2, 0), SemanticVersion(2, 0, 0)),
            copilot_version_status=VersionStatus(
                SemanticVersion(0, 3, 0), SemanticVersion(3, 0, 0)
            ),
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
                call("\nRecommendations:\n", bold=True),
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
                call("\nRecommendations:\n", bold=True),
                call(
                    "  - Upgrade dbt-platform-helper to version 2.0.0 `pip install --upgrade dbt-platform-helper==2.0.0`."
                ),
                call(
                    "    Post upgrade, run `platform-helper copilot make-addons` to update your addon templates."
                ),
                call(""),
            ],
        )

        config_mocks.platform_helper_versioning._get_version_status.assert_called_with(
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
        config_mocks.aws_versioning.get_version_status.assert_called()
        config_mocks.copilot_versioning.get_version_status.assert_called()

    def test_no_platform_config(self, fakefs):
        fakefs.create_file(
            "/copilot/environments/dev/addons/test_addon.yml",
            contents="some other content # Generated by platform-helper v0.1.0 some more content",
        )

        config_mocks = ConfigMocks()
        config_domain = Config(**config_mocks.params())

        with pytest.raises(
            NoPlatformConfigException,
            match="`platform-config.yml` is missing. Please check it exists and you are in the root directory of your deployment project.",
        ) as excinfo:
            config_domain.validate()

    def test_no_copilot_repo(self, fakefs):
        config_domain = Config(sso=Mock())
        with pytest.raises(
            NoDeploymentRepoConfigException,
            match="Could not find a deployment repository, no checks to run.",
        ):
            config_domain.validate()


class TestConfigGenerateAWS:

    @mock.patch.object(builtins, "open", new_callable=mock_open())
    @mock.patch.object(os.path, "expanduser")
    @mock.patch.object(webbrowser, "open")
    def test_aws_with_default_file_path(self, mock_webbrowser_open, mock_expanduser, mock_open):
        config_mocks = ConfigMocks()
        config_mocks.io.confirm.return_value = True
        mock_expanduser.return_value = "/test/aws/config"
        config_domain = Config(**config_mocks.params())

        config_mocks.sso.register.return_value = CLIENT_ID, CLIENT_SECRET

        config_mocks.sso.start_device_authorization.return_value = (
            VERIFICATION_URI,
            "TEST_DEVICE_CODE",
        )

        config_mocks.sso.create_access_token.return_value = "TEST_ACCESS_TOKEN"

        config_mocks.sso.list_accounts.return_value = [
            {
                "accountName": "TEST_AWS_ACCOUNT",
                "accountId": "TEST_AWS_ACCOUNT_ID",
            }
        ]

        config_domain.generate_aws("/test/aws/config")

        config_mocks.sso.register.assert_called_with(
            client_name="platform-helper", client_type="public"
        )
        config_mocks.sso.start_device_authorization.assert_called_with(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            start_url=START_URL,
        )

        config_mocks.io.debug.assert_has_calls(
            [
                call("Creating temporary AWS SSO OIDC application"),
                call("Initiating device code flow"),
            ]
        )

        config_mocks.io.confirm.assert_has_calls(
            [
                call(
                    "You are about to be redirected to a verification page. "
                    "You will need to complete sign-in before returning to the command line. Do you want to continue?"
                ),
                call("Have you completed the sign-in process in your browser?"),
                call(
                    f"This command is destructive and will overwrite file contents at /test/aws/config. Are you sure you want to continue?"
                ),
            ]
        )
        mock_webbrowser_open.assert_called_with(VERIFICATION_URI)
        config_mocks.sso.create_access_token.assert_called_with(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            device_code="TEST_DEVICE_CODE",
        )

        config_mocks.sso.list_accounts.assert_called_with(
            access_token="TEST_ACCESS_TOKEN", max_results=100
        )

        mock_open.return_value.__enter__().write.assert_has_calls(
            [
                call("[profile TEST_AWS_ACCOUNT]\n"),
                call("sso_session = uktrade\n"),
                call("sso_account_id = TEST_AWS_ACCOUNT_ID\n"),
                call("sso_role_name = AdministratorAccess\n"),
                call("region = eu-west-2\n"),
                call("output = json\n"),
                call("\n"),
            ]
        )


class TestConfigMigrate:
    def test_migrate_runs_the_migrator_and_writes_out_its_return_value(self):
        platform_config = {"application": "test-app"}
        migrated_config = {"application": "test-app-modified"}

        config_mocks = ConfigMocks()
        config_domain = Config(**config_mocks.params())
        config_domain.config_provider.load_unvalidated_config_file.return_value = platform_config
        config_domain.migrator.migrate.return_value = migrated_config

        config_domain.config_provider.load_unvalidated_config_file.called_once()
        config_domain.migrator.migrate.assert_called_once_with(platform_config)
        config_domain.config_provider.write_platform_config.assert_called_once_with(migrated_config)
