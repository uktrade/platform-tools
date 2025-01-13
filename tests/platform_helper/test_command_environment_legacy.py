# TODO - "most" of this is now tested by the new test_command_environment, some of this should be delagated to domain-level tests instead.
# Needs reviewing and then the file should be deleted.

from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import patch

import yaml
from click.testing import CliRunner

from dbt_platform_helper.commands.environment import generate
from dbt_platform_helper.commands.environment import offline
from dbt_platform_helper.commands.environment import online
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.providers.load_balancers import ListenerNotFoundException
from dbt_platform_helper.providers.load_balancers import LoadBalancerNotFoundException
from dbt_platform_helper.utils.application import Service
from tests.platform_helper.conftest import BASE_DIR


class TestEnvironmentOfflineCommand:
    @patch("dbt_platform_helper.domain.maintenance_page.load_application")
    @patch(
        "dbt_platform_helper.domain.maintenance_page.find_https_listener",
        return_value="https_listener",
    )
    @patch("dbt_platform_helper.domain.maintenance_page.get_maintenance_page", return_value=None)
    @patch(
        "dbt_platform_helper.domain.maintenance_page.get_env_ips", return_value=["0.1.2.3, 4.5.6.7"]
    )
    @patch("dbt_platform_helper.domain.maintenance_page.add_maintenance_page", return_value=None)
    # TODO this test checks all the submethods are called as expected from the domain class.  Not related to click.  Should be moved to maintenance page domain level tests
    def test_successful_offline(
        self,
        add_maintenance_page,
        get_env_ips,
        get_maintenance_page,
        find_https_listener,
        load_application,
        mock_application,
    ):
        load_application.return_value = mock_application

        result = CliRunner().invoke(
            offline, ["--app", "test-application", "--env", "development"], input="y\n"
        )

        assert (
            "You are about to enable the 'default' maintenance page for the development "
            "environment in test-application."
        ) in result.output
        assert "Would you like to continue? [y/N]: y" in result.output

        find_https_listener.assert_called_with(ANY, "test-application", "development")
        get_maintenance_page.assert_called_with(ANY, "https_listener")
        get_env_ips.assert_called_with(None, mock_application.environments["development"])
        add_maintenance_page.assert_called_with(
            ANY,
            "https_listener",
            "test-application",
            "development",
            [mock_application.services["web"]],
            ["0.1.2.3, 4.5.6.7"],
            "default",
        )

        assert (
            "Maintenance page 'default' added for environment development in "
            "application test-application"
        ) in result.output

    @patch("dbt_platform_helper.domain.maintenance_page.load_application")
    @patch(
        "dbt_platform_helper.domain.maintenance_page.find_https_listener",
        return_value="https_listener",
    )
    @patch("dbt_platform_helper.domain.maintenance_page.get_maintenance_page", return_value=None)
    @patch(
        "dbt_platform_helper.domain.maintenance_page.get_env_ips", return_value=["0.1.2.3, 4.5.6.7"]
    )
    @patch("dbt_platform_helper.domain.maintenance_page.add_maintenance_page", return_value=None)
    # TODO this test checks all the submethods are called as expected from the domain class.  Not related to click.  Should be moved to maintenance page domain level tests
    def test_successful_offline_with_custom_template(
        self,
        add_maintenance_page,
        get_env_ips,
        get_maintenance_page,
        find_https_listener,
        load_application,
        mock_application,
    ):
        load_application.return_value = mock_application

        result = CliRunner().invoke(
            offline,
            ["--app", "test-application", "--env", "development", "--template", "migration"],
            input="y\n",
        )

        assert (
            "You are about to enable the 'migration' maintenance page for the development "
            "environment in test-application."
        ) in result.output
        assert "Would you like to continue? [y/N]: y" in result.output

        find_https_listener.assert_called_with(ANY, "test-application", "development")
        get_maintenance_page.assert_called_with(ANY, "https_listener")
        get_env_ips.assert_called_with(None, mock_application.environments["development"])
        add_maintenance_page.assert_called_with(
            ANY,
            "https_listener",
            "test-application",
            "development",
            [mock_application.services["web"]],
            ["0.1.2.3, 4.5.6.7"],
            "migration",
        )

        assert (
            "Maintenance page 'migration' added for environment development in "
            "application test-application"
        ) in result.output

    @patch("dbt_platform_helper.domain.maintenance_page.load_application")
    @patch(
        "dbt_platform_helper.domain.maintenance_page.find_https_listener",
        return_value="https_listener",
    )
    @patch(
        "dbt_platform_helper.domain.maintenance_page.get_maintenance_page",
        return_value="maintenance",
    )
    @patch("dbt_platform_helper.domain.maintenance_page.remove_maintenance_page", return_value=None)
    @patch(
        "dbt_platform_helper.domain.maintenance_page.get_env_ips", return_value=["0.1.2.3, 4.5.6.7"]
    )
    @patch("dbt_platform_helper.domain.maintenance_page.add_maintenance_page", return_value=None)
    # TODO move to domain level test for the activate function
    def test_successful_offline_when_already_offline(
        self,
        add_maintenance_page,
        get_env_ips,
        remove_maintenance_page,
        get_maintenance_page,
        find_https_listener,
        load_application,
        mock_application,
    ):
        load_application.return_value = mock_application

        result = CliRunner().invoke(
            offline, ["--app", "test-application", "--env", "development"], input="y\n"
        )

        assert (
            "There is currently a 'maintenance' maintenance page for the development "
            "environment in test-application."
        ) in result.output
        assert (
            "Would you like to replace it with a 'default' maintenance page? [y/N]: y"
            in result.output
        )

        find_https_listener.assert_called_with(ANY, "test-application", "development")
        get_maintenance_page.assert_called_with(ANY, "https_listener")
        remove_maintenance_page.assert_called_with(ANY, "https_listener")
        get_env_ips.assert_called_with(None, mock_application.environments["development"])
        add_maintenance_page.assert_called_with(
            ANY,
            "https_listener",
            "test-application",
            "development",
            [mock_application.services["web"]],
            ["0.1.2.3, 4.5.6.7"],
            "default",
        )

        assert (
            "Maintenance page 'default' added for environment development in "
            "application test-application"
        ) in result.output

    @patch("dbt_platform_helper.domain.maintenance_page.load_application")
    @patch("dbt_platform_helper.domain.maintenance_page.find_https_listener")
    @patch("dbt_platform_helper.domain.maintenance_page.get_maintenance_page")
    @patch("dbt_platform_helper.domain.maintenance_page.remove_maintenance_page")
    @patch("dbt_platform_helper.domain.maintenance_page.add_maintenance_page")
    # TODO move to domain level test for the activate function
    def test_offline_an_environment_when_load_balancer_not_found(
        self,
        add_maintenance_page,
        remove_maintenance_page,
        get_maintenance_page,
        find_https_listener,
        load_application,
        mock_application,
    ):
        find_https_listener.side_effect = LoadBalancerNotFoundException()
        load_application.return_value = mock_application

        result = CliRunner().invoke(
            offline, ["--app", "test-application", "--env", "development"], input="y\n"
        )

        assert (
            "No load balancer found for environment development in the application "
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
    @patch("dbt_platform_helper.domain.maintenance_page.add_maintenance_page")
    # TODO move to domain level test for the activate function
    def test_offline_an_environment_when_listener_not_found(
        self,
        add_maintenance_page,
        remove_maintenance_page,
        get_maintenance_page,
        find_https_listener,
        load_application,
        mock_application,
    ):
        load_application.return_value = mock_application
        find_https_listener.side_effect = ListenerNotFoundException()

        result = CliRunner().invoke(
            offline, ["--app", "test-application", "--env", "development"], input="y\n"
        )

        assert (
            "No HTTPS listener found for environment development in the application "
            "test-application."
        ) in result.output
        assert "Aborted!" in result.output

        find_https_listener.assert_called_with(ANY, "test-application", "development")
        get_maintenance_page.assert_not_called()
        remove_maintenance_page.assert_not_called()
        add_maintenance_page.assert_not_called()

    @patch("dbt_platform_helper.domain.maintenance_page.load_application")
    @patch(
        "dbt_platform_helper.domain.maintenance_page.find_https_listener",
        return_value="https_listener",
    )
    @patch("dbt_platform_helper.domain.maintenance_page.get_maintenance_page", return_value=None)
    @patch(
        "dbt_platform_helper.domain.maintenance_page.get_env_ips", return_value=["0.1.2.3, 4.5.6.7"]
    )
    @patch("dbt_platform_helper.domain.maintenance_page.add_maintenance_page", return_value=None)
    # TODO move to domain level test for the activate function
    def test_successful_offline_multiple_services(
        self,
        add_maintenance_page,
        get_env_ips,
        get_maintenance_page,
        find_https_listener,
        load_application,
        mock_application,
    ):
        mock_application.services["web2"] = Service("web2", "Load Balanced Web Service")
        load_application.return_value = mock_application

        result = CliRunner().invoke(
            offline,
            ["--app", "test-application", "--env", "development", "--svc", "*"],
            input="y\n",
        )

        assert (
            "You are about to enable the 'default' maintenance page for the development "
            "environment in test-application."
        ) in result.output
        assert "Would you like to continue? [y/N]: y" in result.output

        find_https_listener.assert_called_with(ANY, "test-application", "development")
        get_maintenance_page.assert_called_with(ANY, "https_listener")
        get_env_ips.assert_called_with(None, mock_application.environments["development"])
        add_maintenance_page.assert_called_with(
            ANY,
            "https_listener",
            "test-application",
            "development",
            [mock_application.services["web"], mock_application.services["web2"]],
            ["0.1.2.3, 4.5.6.7"],
            "default",
        )

        assert (
            "Maintenance page 'default' added for environment development in "
            "application test-application"
        ) in result.output


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

    # @patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    # @patch(
    #     "dbt_platform_helper.domain.copilot_environment.get_cert_arn",
    #     return_value="arn:aws:acm:test",
    # )
    # @patch(
    #     "dbt_platform_helper.domain.copilot_environment.get_subnet_ids",
    #     return_value=(["def456"], ["ghi789"]),
    # )
    # @patch("dbt_platform_helper.domain.copilot_environment.get_vpc_id", return_value="vpc-abc123")
    # @patch("dbt_platform_helper.domain.copilot_environment.get_aws_session_or_abort")
    # @pytest.mark.parametrize(
    #     "environment_config, expected_vpc",
    #     [
    #         ({"test": {}}, None),
    #         ({"test": {"vpc": "vpc1"}}, "vpc1"),
    #         ({"*": {"vpc": "vpc2"}, "test": None}, "vpc2"),
    #         ({"*": {"vpc": "vpc3"}, "test": {"vpc": "vpc4"}}, "vpc4"),
    #     ],
    # )
    # def test_generate(
    #     self,
    #     mock_get_aws_session_1,
    #     mock_get_vpc_id,
    #     mock_get_subnet_ids,
    #     mock_get_cert_arn,
    #     fakefs,
    #     environment_config,
    #     expected_vpc,
    # ):
    #     # TODO can mock ConfigProvier instead to set up config
    #     default_conf = environment_config.get("*", {})
    #     default_conf["accounts"] = {
    #         "deploy": {"name": "non-prod-acc", "id": "1122334455"},
    #         "dns": {"name": "non-prod-dns-acc", "id": "6677889900"},
    #     }
    #     environment_config["*"] = default_conf

    #     fakefs.create_file(
    #         PLATFORM_CONFIG_FILE,
    #         contents=yaml.dump({"application": "my-app", "environments": environment_config}),
    #     )

    #     mocked_session = MagicMock()
    #     mock_get_aws_session_1.return_value = mocked_session
    #     fakefs.add_real_directory(
    #         BASE_DIR / "tests" / "platform_helper", read_only=False, target_path="copilot"
    #     )

    #     result = CliRunner().invoke(generate, ["--name", "test"])

    #     # Comparing the generated file with the expected file - domain level test.
    #     # TODO Check file provider has been called on the expected contents instead of using fakefs.
    #     actual = yaml.safe_load(Path("copilot/environments/test/manifest.yml").read_text())
    #     expected = yaml.safe_load(
    #         Path("copilot/fixtures/test_environment_manifest.yml").read_text()
    #     )

    #     # Checking functions are called as expected - domain level test
    #     # TODO get_vpc_id should be replaced with VpcProvider
    #     mock_get_vpc_id.assert_called_once_with(mocked_session, "test", expected_vpc)
    #     mock_get_subnet_ids.assert_called_once_with(mocked_session, "vpc-abc123", "test")
    #     mock_get_cert_arn.assert_called_once_with(mocked_session, "my-app", "test")
    #     mock_get_aws_session_1.assert_called_once_with("non-prod-acc")

    #     assert actual == expected

    #     # TODO Check output of command - domain level test
    #     assert "File copilot/environments/test/manifest.yml created" in result.output

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
