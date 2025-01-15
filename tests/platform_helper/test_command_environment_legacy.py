# TODO - "most" of this is now tested by the new test_command_environment, some of this should be delagated to domain-level tests instead.
# Needs reviewing and then the file should be deleted.

from pathlib import Path
from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from dbt_platform_helper.commands.environment import generate
from dbt_platform_helper.commands.environment import online
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.providers.load_balancers import ListenerNotFoundException
from dbt_platform_helper.providers.load_balancers import LoadBalancerNotFoundException
from tests.platform_helper.conftest import BASE_DIR


class TestEnvironmentOnlineCommand:
    @patch("dbt_platform_helper.domain.maintenance_page.load_application")
    @patch(
        "dbt_platform_helper.domain.maintenance_page.find_https_listener",
        return_value="https_listener",
    )
    @patch(
        "dbt_platform_helper.domain.maintenance_page.get_maintenance_page", return_value="default"
    )
    @patch("dbt_platform_helper.domain.maintenance_page.remove_maintenance_page", return_value=None)
    # TODO move to domain level test for the deactivate function
    def test_successful_online(
        self,
        remove_maintenance_page,
        get_maintenance_page,
        find_https_listener,
        load_application,
        mock_application,
    ):
        load_application.return_value = mock_application

        result = CliRunner().invoke(
            online, ["--app", "test-application", "--env", "development"], input="y\n"
        )

        assert (
            "There is currently a 'default' maintenance page, would you like to remove it? "
            "[y/N]: y"
        ) in result.output

        find_https_listener.assert_called_with(ANY, "test-application", "development")
        get_maintenance_page.assert_called_with(ANY, "https_listener")
        remove_maintenance_page.assert_called_with(ANY, "https_listener")

        assert (
            "Maintenance page removed from environment development in "
            "application test-application"
        ) in result.output

    @patch("dbt_platform_helper.domain.maintenance_page.load_application")
    @patch(
        "dbt_platform_helper.domain.maintenance_page.find_https_listener",
        return_value="https_listener",
    )
    @patch("dbt_platform_helper.domain.maintenance_page.get_maintenance_page", return_value=None)
    @patch("dbt_platform_helper.domain.maintenance_page.remove_maintenance_page", return_value=None)
    # TODO move to domain level test for the deactivate function
    def test_online_an_environment_that_is_not_offline(
        self,
        remove_maintenance_page,
        get_maintenance_page,
        find_https_listener,
        load_application,
        mock_application,
    ):
        load_application.return_value = mock_application

        result = CliRunner().invoke(
            online, ["--app", "test-application", "--env", "development"], input="y\n"
        )

        assert "There is no current maintenance page to remove" in result.output

        find_https_listener.assert_called_with(ANY, "test-application", "development")
        get_maintenance_page.assert_called_with(ANY, "https_listener")
        remove_maintenance_page.assert_not_called()

    @patch("dbt_platform_helper.domain.maintenance_page.load_application")
    @patch("dbt_platform_helper.domain.maintenance_page.find_https_listener")
    @patch("dbt_platform_helper.domain.maintenance_page.get_maintenance_page")
    @patch("dbt_platform_helper.domain.maintenance_page.remove_maintenance_page")
    # TODO move to domain level test for the deactivate function
    def test_online_an_environment_when_listener_not_found(
        self,
        remove_maintenance_page,
        get_maintenance_page,
        find_https_listener,
        load_application,
        mock_application,
    ):
        load_application.return_value = mock_application
        find_https_listener.side_effect = ListenerNotFoundException()

        result = CliRunner().invoke(
            online, ["--app", "test-application", "--env", "development"], input="y\n"
        )

        assert (
            "No HTTPS listener found for environment development in the application "
            "test-application."
        ) in result.output
        assert "Aborted!" in result.output

        find_https_listener.assert_called_with(ANY, "test-application", "development")
        get_maintenance_page.assert_not_called()
        remove_maintenance_page.assert_not_called()

    @patch("dbt_platform_helper.domain.maintenance_page.load_application")
    @patch("dbt_platform_helper.domain.maintenance_page.find_https_listener")
    @patch("dbt_platform_helper.domain.maintenance_page.get_maintenance_page")
    @patch("dbt_platform_helper.domain.maintenance_page.remove_maintenance_page")
    # TODO move to domain level test for the deactivate function
    def test_online_an_environment_when_load_balancer_not_found(
        self,
        remove_maintenance_page,
        get_maintenance_page,
        find_https_listener,
        load_application,
        mock_application,
    ):
        from dbt_platform_helper.commands.environment import online

        load_application.return_value = mock_application
        find_https_listener.side_effect = LoadBalancerNotFoundException()

        result = CliRunner().invoke(
            online, ["--app", "test-application", "--env", "development"], input="y\n"
        )

        assert (
            "No load balancer found for environment development in the application "
            "test-application."
        ) in result.output
        assert "Aborted!" in result.output

        find_https_listener.assert_called_with(ANY, "test-application", "development")
        get_maintenance_page.assert_not_called()
        remove_maintenance_page.assert_not_called()


class TestGenerate:

    @patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    @patch(
        "dbt_platform_helper.domain.copilot_environment.get_cert_arn",
        return_value="arn:aws:acm:test",
    )
    @patch(
        "dbt_platform_helper.domain.copilot_environment.get_subnet_ids",
        return_value=(["def456"], ["ghi789"]),
    )
    @patch("dbt_platform_helper.domain.copilot_environment.get_vpc_id", return_value="vpc-abc123")
    @patch("dbt_platform_helper.domain.copilot_environment.get_aws_session_or_abort")
    @pytest.mark.parametrize(
        "environment_config, expected_vpc",
        [
            ({"test": {}}, None),
            ({"test": {"vpc": "vpc1"}}, "vpc1"),
            ({"*": {"vpc": "vpc2"}, "test": None}, "vpc2"),
            ({"*": {"vpc": "vpc3"}, "test": {"vpc": "vpc4"}}, "vpc4"),
        ],
    )
    def test_generate(
        self,
        mock_get_aws_session_1,
        mock_get_vpc_id,
        mock_get_subnet_ids,
        mock_get_cert_arn,
        fakefs,
        environment_config,
        expected_vpc,
    ):
        # TODO can mock ConfigProvier instead to set up config
        default_conf = environment_config.get("*", {})
        default_conf["accounts"] = {
            "deploy": {"name": "non-prod-acc", "id": "1122334455"},
            "dns": {"name": "non-prod-dns-acc", "id": "6677889900"},
        }
        environment_config["*"] = default_conf

        fakefs.create_file(
            PLATFORM_CONFIG_FILE,
            contents=yaml.dump({"application": "my-app", "environments": environment_config}),
        )

        mocked_session = MagicMock()
        mock_get_aws_session_1.return_value = mocked_session
        fakefs.add_real_directory(
            BASE_DIR / "tests" / "platform_helper", read_only=False, target_path="copilot"
        )

        result = CliRunner().invoke(generate, ["--name", "test"])

        # Comparing the generated file with the expected file - domain level test.
        # TODO Check file provider has been called on the expected contents instead of using fakefs.
        actual = yaml.safe_load(Path("copilot/environments/test/manifest.yml").read_text())
        expected = yaml.safe_load(
            Path("copilot/fixtures/test_environment_manifest.yml").read_text()
        )

        # Checking functions are called as expected - domain level test
        # TODO get_vpc_id should be replaced with VpcProvider
        mock_get_vpc_id.assert_called_once_with(mocked_session, "test", expected_vpc)
        mock_get_subnet_ids.assert_called_once_with(mocked_session, "vpc-abc123", "test")
        mock_get_cert_arn.assert_called_once_with(mocked_session, "my-app", "test")
        mock_get_aws_session_1.assert_called_once_with("non-prod-acc")

        assert actual == expected

        # TODO Check output of command - domain level test
        assert "File copilot/environments/test/manifest.yml created" in result.output

    @patch("dbt_platform_helper.domain.copilot_environment.get_aws_session_or_abort")
    # TODO Can be tested at domain level with a mocked config provider
    def test_fail_early_if_platform_config_invalid(self, mock_session_1, fakefs):

        fakefs.add_real_directory(
            BASE_DIR / "tests" / "platform_helper", read_only=False, target_path="copilot"
        )
        content = yaml.dump({})
        fakefs.create_file(PLATFORM_CONFIG_FILE, contents=content)

        mock_session = MagicMock()
        mock_session_1.return_value = mock_session

        result = CliRunner().invoke(generate, ["--name", "test"])

        assert result.exit_code != 0
        assert "Missing key: 'application'" in result.output
