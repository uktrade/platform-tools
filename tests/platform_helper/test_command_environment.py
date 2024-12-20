from pathlib import Path
from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from dbt_platform_helper.commands.environment import generate
from dbt_platform_helper.commands.environment import generate_terraform
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
        default_conf = environment_config.get("*", {})
        default_conf["accounts"] = {
            "deploy": {"name": "non-prod-acc", "id": "1122334455"},
            "dns": {"name": "non-prod-dns-acc", "id": "6677889900"},
        }
        environment_config["*"] = default_conf

        mocked_session = MagicMock()
        mock_get_aws_session_1.return_value = mocked_session
        fakefs.add_real_directory(
            BASE_DIR / "tests" / "platform_helper", read_only=False, target_path="copilot"
        )
        fakefs.create_file(
            PLATFORM_CONFIG_FILE,
            contents=yaml.dump({"application": "my-app", "environments": environment_config}),
        )

        result = CliRunner().invoke(generate, ["--name", "test"])
        actual = yaml.safe_load(Path("copilot/environments/test/manifest.yml").read_text())
        expected = yaml.safe_load(
            Path("copilot/fixtures/test_environment_manifest.yml").read_text()
        )

        mock_get_vpc_id.assert_called_once_with(mocked_session, "test", expected_vpc)
        mock_get_subnet_ids.assert_called_once_with(mocked_session, "vpc-abc123", "test")
        mock_get_cert_arn.assert_called_once_with(mocked_session, "my-app", "test")
        mock_get_aws_session_1.assert_called_once_with("non-prod-acc")

        assert actual == expected
        assert "File copilot/environments/test/manifest.yml created" in result.output

    @patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    @patch("dbt_platform_helper.domain.copilot_environment.get_aws_session_or_abort")
    @pytest.mark.parametrize(
        "env_modules_version, cli_modules_version, expected_version, should_include_moved_block",
        [
            (None, None, "5", True),
            ("7", None, "7", True),
            (None, "8", "8", True),
            ("9", "10", "10", True),
            ("9-tf", "10", "10", True),
        ],
    )
    def test_generate_terraform(
        self,
        mock_get_aws_session_1,
        fakefs,
        env_modules_version,
        cli_modules_version,
        expected_version,
        should_include_moved_block,
    ):

        environment_config = {
            "*": {
                "vpc": "vpc3",
                "accounts": {
                    "deploy": {"name": "non-prod-acc", "id": "1122334455"},
                    "dns": {"name": "non-prod-dns-acc", "id": "6677889900"},
                },
            },
            "test": None,
        }

        if env_modules_version:
            environment_config["test"] = {
                "versions": {"terraform-platform-modules": env_modules_version}
            }

        mocked_session = MagicMock()
        mock_get_aws_session_1.return_value = mocked_session
        fakefs.add_real_directory(
            BASE_DIR / "tests" / "platform_helper", read_only=False, target_path="copilot"
        )
        fakefs.create_file(
            PLATFORM_CONFIG_FILE,
            contents=yaml.dump({"application": "my-app", "environments": environment_config}),
        )

        args = ["--name", "test"]
        if cli_modules_version:
            args.extend(["--terraform-platform-modules-version", cli_modules_version])

        result = CliRunner().invoke(generate_terraform, args)

        assert "File terraform/environments/test/main.tf created" in result.output
        main_tf = Path("terraform/environments/test/main.tf")
        assert main_tf.exists()
        content = main_tf.read_text()

        assert "# WARNING: This is an autogenerated file, not for manual editing." in content
        assert (
            f"git::https://github.com/uktrade/terraform-platform-modules.git//extensions?depth=1&ref={expected_version}"
            in content
        )
        moved_block = "moved {\n  from = module.extensions-tf\n  to   = module.extensions\n}\n"
        assert moved_block in content

    @patch("dbt_platform_helper.domain.copilot_environment.get_aws_session_or_abort")
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

    def test_fail_with_explanation_if_vpc_name_option_used(self, fakefs):

        fakefs.add_real_directory(
            BASE_DIR / "tests" / "platform_helper", read_only=False, target_path="copilot"
        )
        fakefs.create_file(PLATFORM_CONFIG_FILE, contents=yaml.dump({"application": "my-app"}))

        result = CliRunner().invoke(generate, ["--name", "test", "--vpc-name", "other-vpc"])

        assert result.exit_code != 0
        assert (
            f"This option is deprecated. Please add the VPC name for your envs to {PLATFORM_CONFIG_FILE}"
            in result.output
        )
