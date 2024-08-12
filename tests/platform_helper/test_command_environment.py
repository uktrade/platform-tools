from pathlib import Path
from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import call
from unittest.mock import patch

import boto3
import click
import pytest
import yaml
from click.testing import CliRunner
from moto import mock_aws

from dbt_platform_helper.utils.application import Service
from dbt_platform_helper.utils.files import PLATFORM_CONFIG_FILE
from tests.platform_helper.conftest import BASE_DIR


class TestEnvironmentOfflineCommand:
    @patch("dbt_platform_helper.commands.environment.load_application")
    @patch(
        "dbt_platform_helper.commands.environment.find_https_listener",
        return_value="https_listener",
    )
    @patch("dbt_platform_helper.commands.environment.get_maintenance_page", return_value=None)
    @patch(
        "dbt_platform_helper.commands.environment.get_env_ips", return_value=["0.1.2.3, 4.5.6.7"]
    )
    @patch("dbt_platform_helper.commands.environment.add_maintenance_page", return_value=None)
    def test_successful_offline(
        self,
        add_maintenance_page,
        get_env_ips,
        get_maintenance_page,
        find_https_listener,
        load_application,
        mock_application,
    ):
        from dbt_platform_helper.commands.environment import offline

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

    @patch("dbt_platform_helper.commands.environment.load_application")
    @patch(
        "dbt_platform_helper.commands.environment.find_https_listener",
        return_value="https_listener",
    )
    @patch("dbt_platform_helper.commands.environment.get_maintenance_page", return_value=None)
    @patch(
        "dbt_platform_helper.commands.environment.get_env_ips", return_value=["0.1.2.3, 4.5.6.7"]
    )
    @patch("dbt_platform_helper.commands.environment.add_maintenance_page", return_value=None)
    def test_successful_offline_with_custom_template(
        self,
        add_maintenance_page,
        get_env_ips,
        get_maintenance_page,
        find_https_listener,
        load_application,
        mock_application,
    ):
        from dbt_platform_helper.commands.environment import offline

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

    @patch("dbt_platform_helper.commands.environment.load_application")
    @patch(
        "dbt_platform_helper.commands.environment.find_https_listener",
        return_value="https_listener",
    )
    @patch(
        "dbt_platform_helper.commands.environment.get_maintenance_page", return_value="maintenance"
    )
    @patch("dbt_platform_helper.commands.environment.remove_maintenance_page", return_value=None)
    @patch(
        "dbt_platform_helper.commands.environment.get_env_ips", return_value=["0.1.2.3, 4.5.6.7"]
    )
    @patch("dbt_platform_helper.commands.environment.add_maintenance_page", return_value=None)
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
        from dbt_platform_helper.commands.environment import offline

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

    @patch("dbt_platform_helper.commands.environment.load_application")
    @patch("dbt_platform_helper.commands.environment.find_https_listener")
    @patch("dbt_platform_helper.commands.environment.get_maintenance_page")
    @patch("dbt_platform_helper.commands.environment.remove_maintenance_page")
    @patch("dbt_platform_helper.commands.environment.add_maintenance_page")
    def test_offline_an_environment_when_load_balancer_not_found(
        self,
        add_maintenance_page,
        remove_maintenance_page,
        get_maintenance_page,
        find_https_listener,
        load_application,
        mock_application,
    ):
        from dbt_platform_helper.commands.environment import LoadBalancerNotFoundError
        from dbt_platform_helper.commands.environment import offline

        find_https_listener.side_effect = LoadBalancerNotFoundError()
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

    @patch("dbt_platform_helper.commands.environment.load_application")
    @patch("dbt_platform_helper.commands.environment.find_https_listener")
    @patch("dbt_platform_helper.commands.environment.get_maintenance_page")
    @patch("dbt_platform_helper.commands.environment.remove_maintenance_page")
    @patch("dbt_platform_helper.commands.environment.add_maintenance_page")
    def test_offline_an_environment_when_listener_not_found(
        self,
        add_maintenance_page,
        remove_maintenance_page,
        get_maintenance_page,
        find_https_listener,
        load_application,
        mock_application,
    ):
        from dbt_platform_helper.commands.environment import ListenerNotFoundError
        from dbt_platform_helper.commands.environment import offline

        load_application.return_value = mock_application
        find_https_listener.side_effect = ListenerNotFoundError()

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

    @patch("dbt_platform_helper.commands.environment.load_application")
    @patch(
        "dbt_platform_helper.commands.environment.find_https_listener",
        return_value="https_listener",
    )
    @patch("dbt_platform_helper.commands.environment.get_maintenance_page", return_value=None)
    @patch(
        "dbt_platform_helper.commands.environment.get_env_ips", return_value=["0.1.2.3, 4.5.6.7"]
    )
    @patch("dbt_platform_helper.commands.environment.add_maintenance_page", return_value=None)
    def test_successful_offline_multiple_services(
        self,
        add_maintenance_page,
        get_env_ips,
        get_maintenance_page,
        find_https_listener,
        load_application,
        mock_application,
    ):
        from dbt_platform_helper.commands.environment import offline

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
    @patch("dbt_platform_helper.commands.environment.load_application")
    @patch(
        "dbt_platform_helper.commands.environment.find_https_listener",
        return_value="https_listener",
    )
    @patch("dbt_platform_helper.commands.environment.get_maintenance_page", return_value="default")
    @patch("dbt_platform_helper.commands.environment.remove_maintenance_page", return_value=None)
    def test_successful_online(
        self,
        remove_maintenance_page,
        get_maintenance_page,
        find_https_listener,
        load_application,
        mock_application,
    ):
        from dbt_platform_helper.commands.environment import online

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

    @patch("dbt_platform_helper.commands.environment.load_application")
    @patch(
        "dbt_platform_helper.commands.environment.find_https_listener",
        return_value="https_listener",
    )
    @patch("dbt_platform_helper.commands.environment.get_maintenance_page", return_value=None)
    @patch("dbt_platform_helper.commands.environment.remove_maintenance_page", return_value=None)
    def test_online_an_environment_that_is_not_offline(
        self,
        remove_maintenance_page,
        get_maintenance_page,
        find_https_listener,
        load_application,
        mock_application,
    ):
        from dbt_platform_helper.commands.environment import online

        load_application.return_value = mock_application

        result = CliRunner().invoke(
            online, ["--app", "test-application", "--env", "development"], input="y\n"
        )

        assert "There is no current maintenance page to remove" in result.output

        find_https_listener.assert_called_with(ANY, "test-application", "development")
        get_maintenance_page.assert_called_with(ANY, "https_listener")
        remove_maintenance_page.assert_not_called()

    @patch("dbt_platform_helper.commands.environment.load_application")
    @patch("dbt_platform_helper.commands.environment.find_https_listener")
    @patch("dbt_platform_helper.commands.environment.get_maintenance_page")
    @patch("dbt_platform_helper.commands.environment.remove_maintenance_page")
    def test_online_an_environment_when_listener_not_found(
        self,
        remove_maintenance_page,
        get_maintenance_page,
        find_https_listener,
        load_application,
        mock_application,
    ):
        from dbt_platform_helper.commands.environment import ListenerNotFoundError
        from dbt_platform_helper.commands.environment import online

        load_application.return_value = mock_application
        find_https_listener.side_effect = ListenerNotFoundError()

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

    @patch("dbt_platform_helper.commands.environment.load_application")
    @patch("dbt_platform_helper.commands.environment.find_https_listener")
    @patch("dbt_platform_helper.commands.environment.get_maintenance_page")
    @patch("dbt_platform_helper.commands.environment.remove_maintenance_page")
    def test_online_an_environment_when_load_balancer_not_found(
        self,
        remove_maintenance_page,
        get_maintenance_page,
        find_https_listener,
        load_application,
        mock_application,
    ):
        from dbt_platform_helper.commands.environment import LoadBalancerNotFoundError
        from dbt_platform_helper.commands.environment import online

        load_application.return_value = mock_application
        find_https_listener.side_effect = LoadBalancerNotFoundError()

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
    @patch("dbt_platform_helper.commands.environment.get_cert_arn", return_value="arn:aws:acm:test")
    @patch(
        "dbt_platform_helper.commands.environment.get_subnet_ids",
        return_value=(["def456"], ["ghi789"]),
    )
    @patch("dbt_platform_helper.commands.environment.get_vpc_id", return_value="vpc-abc123")
    @patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.environment.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.environment.is_terraform_project")
    @pytest.mark.parametrize("is_terraform", [True, False])
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
        mock_is_terraform_project,
        mock_get_aws_session_1,
        mock_get_aws_session_2,
        mock_get_vpc_id,
        mock_get_subnet_ids,
        mock_get_cert_arn,
        fakefs,
        is_terraform,
        environment_config,
        expected_vpc,
    ):
        from dbt_platform_helper.commands.environment import generate

        default_conf = environment_config.get("*", {})
        default_conf["accounts"] = {
            "deploy": {"name": "non-prod-acc", "id": "1122334455"},
            "dns": {"name": "non-prod-dns-acc", "id": "6677889900"},
        }
        environment_config["*"] = default_conf

        mocked_session = MagicMock()
        mock_get_aws_session_1.return_value = mocked_session
        mock_get_aws_session_2.return_value = mocked_session
        fakefs.add_real_directory(
            BASE_DIR / "tests" / "platform_helper", read_only=False, target_path="copilot"
        )
        fakefs.create_file(
            PLATFORM_CONFIG_FILE,
            contents=yaml.dump({"application": "my-app", "environments": environment_config}),
        )
        mock_is_terraform_project.return_value = is_terraform

        result = CliRunner().invoke(generate, ["--name", "test"])

        actual = yaml.safe_load(Path("copilot/environments/test/manifest.yml").read_text())
        expected = yaml.safe_load(
            Path("copilot/fixtures/test_environment_manifest.yml").read_text()
        )

        mock_get_vpc_id.assert_called_once_with(mocked_session, "test", expected_vpc)
        mock_get_subnet_ids.assert_called_once_with(mocked_session, "vpc-abc123")
        mock_get_cert_arn.assert_called_once_with(mocked_session, "test")

        assert actual == expected
        assert "File copilot/environments/test/manifest.yml created" in result.output

    @patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    @patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.environment.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.environment.is_terraform_project", return_value=True)
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
        mock_is_terraform_project,
        mock_get_aws_session_1,
        mock_get_aws_session_2,
        fakefs,
        env_modules_version,
        cli_modules_version,
        expected_version,
        should_include_moved_block,
    ):
        from dbt_platform_helper.commands.environment import generate_terraform

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
        mock_get_aws_session_2.return_value = mocked_session
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

    @patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    @patch("dbt_platform_helper.commands.environment.is_terraform_project", return_value=False)
    def test_generate_terraform_errors_if_this_is_a_legacy_project(
        self,
        mock_is_terraform_project,
        fakefs,
    ):
        from dbt_platform_helper.commands.environment import generate_terraform

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

        fakefs.create_file(
            PLATFORM_CONFIG_FILE,
            contents=yaml.dump(
                {
                    "application": "my-app",
                    "legacy_project": True,
                    "environments": environment_config,
                }
            ),
        )

        result = CliRunner().invoke(generate_terraform, ["--name", "test"])

        assert result.exit_code != 0
        assert "This is not a terraform project. Exiting." in result.output

    @patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.environment.get_aws_session_or_abort")
    def test_fail_early_if_platform_config_invalid(self, mock_session_1, mock_session_2, fakefs):
        from dbt_platform_helper.commands.environment import generate

        fakefs.add_real_directory(
            BASE_DIR / "tests" / "platform_helper", read_only=False, target_path="copilot"
        )
        content = yaml.dump({})
        fakefs.create_file(PLATFORM_CONFIG_FILE, contents=content)

        mock_session = MagicMock()
        mock_session_1.return_value = mock_session
        mock_session_2.return_value = mock_session

        result = CliRunner().invoke(generate, ["--name", "test"])

        assert result.exit_code != 0
        assert "Missing key: 'application'" in result.output

    def test_fail_with_explanation_if_vpc_name_option_used(self, fakefs):
        from dbt_platform_helper.commands.environment import generate

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

    @pytest.mark.parametrize("vpc_name", ["default", "default-prod"])
    @mock_aws
    def test_get_vpc_id(self, vpc_name):
        from dbt_platform_helper.commands.environment import get_vpc_id

        session = boto3.session.Session()
        vpc = session.client("ec2").create_vpc(
            CidrBlock="10.0.0.0/16",
            TagSpecifications=[
                {
                    "ResourceType": "vpc",
                    "Tags": [
                        {"Key": "Name", "Value": vpc_name},
                    ],
                },
            ],
        )["Vpc"]
        expected_vpc_id = vpc["VpcId"]

        actual_vpc_id = get_vpc_id(session, "prod")

        assert expected_vpc_id == actual_vpc_id

        vpc_id_from_name = get_vpc_id(session, "not-an-env", vpc_name=vpc_name)

        assert expected_vpc_id == vpc_id_from_name

    @mock_aws
    def test_get_vpc_id_failure(self, capsys):
        from dbt_platform_helper.commands.environment import get_vpc_id

        with pytest.raises(click.Abort):
            get_vpc_id(boto3.session.Session(), "development")

        captured = capsys.readouterr()

        assert "No VPC found with name default-development in AWS account default." in captured.out

    @mock_aws
    def test_get_subnet_ids(self):
        from dbt_platform_helper.commands.environment import get_subnet_ids

        session = boto3.session.Session()
        vpc = session.client("ec2").create_vpc(
            CidrBlock="10.0.0.0/16",
            TagSpecifications=[
                {
                    "ResourceType": "vpc",
                    "Tags": [
                        {"Key": "Name", "Value": "default-development"},
                    ],
                },
            ],
        )["Vpc"]
        public_subnet = session.client("ec2").create_subnet(
            CidrBlock="10.0.128.0/24",
            VpcId=vpc["VpcId"],
            TagSpecifications=[
                {
                    "ResourceType": "subnet",
                    "Tags": [
                        {"Key": "subnet_type", "Value": "public"},
                    ],
                },
            ],
        )["Subnet"]
        private_subnet = session.client("ec2").create_subnet(
            CidrBlock="10.0.1.0/24",
            VpcId=vpc["VpcId"],
            TagSpecifications=[
                {
                    "ResourceType": "subnet",
                    "Tags": [
                        {"Key": "subnet_type", "Value": "private"},
                    ],
                },
            ],
        )["Subnet"]

        public, private = get_subnet_ids(session, vpc["VpcId"])

        assert public == [public_subnet["SubnetId"]]
        assert private == [private_subnet["SubnetId"]]

    @mock_aws
    def test_get_subnet_ids_failure(self, capsys):
        from dbt_platform_helper.commands.environment import get_subnet_ids

        with pytest.raises(click.Abort):
            get_subnet_ids(boto3.session.Session(), "123")

        captured = capsys.readouterr()

        assert "No subnets found for VPC with id: 123." in captured.out

    @mock_aws
    def test_get_cert_arn(self):
        from dbt_platform_helper.commands.environment import get_cert_arn

        session = boto3.session.Session()
        expected_arn = session.client("acm").request_certificate(DomainName="development.com")[
            "CertificateArn"
        ]

        actual_arn = get_cert_arn(session, "development")

        assert expected_arn == actual_arn

    @mock_aws
    def test_cert_arn_failure(self, capsys):
        from dbt_platform_helper.commands.environment import get_cert_arn

        with pytest.raises(click.Abort):
            get_cert_arn(boto3.session.Session(), "development")

        captured = capsys.readouterr()

        assert (
            "No certificate found with domain name matching environment development."
            in captured.out
        )


class TestFindLoadBalancer:
    def test_when_no_load_balancer_exists(self):
        from dbt_platform_helper.commands.environment import LoadBalancerNotFoundError
        from dbt_platform_helper.commands.environment import find_load_balancer

        boto_mock = MagicMock()
        boto_mock.client().describe_load_balancers.return_value = {"LoadBalancers": []}
        with pytest.raises(LoadBalancerNotFoundError):
            find_load_balancer(boto_mock, "test-application", "development")

    def test_when_a_load_balancer_exists(self):
        from dbt_platform_helper.commands.environment import find_load_balancer

        boto_mock = MagicMock()
        boto_mock.client().describe_load_balancers.return_value = {
            "LoadBalancers": [{"LoadBalancerArn": "lb_arn"}]
        }
        boto_mock.client().describe_tags.return_value = {
            "TagDescriptions": [
                {
                    "ResourceArn": "lb_arn",
                    "Tags": [
                        {"Key": "copilot-application", "Value": "test-application"},
                        {"Key": "copilot-environment", "Value": "development"},
                    ],
                }
            ]
        }

        lb_arn = find_load_balancer(boto_mock, "test-application", "development")
        assert "lb_arn" == lb_arn


class TestFindHTTPSListener:
    @patch("dbt_platform_helper.commands.environment.find_load_balancer", return_value="lb_arn")
    def test_when_no_https_listener_present(self, find_load_balancer):
        from dbt_platform_helper.commands.environment import ListenerNotFoundError
        from dbt_platform_helper.commands.environment import find_https_listener

        boto_mock = MagicMock()
        boto_mock.client().describe_listeners.return_value = {"Listeners": []}
        with pytest.raises(ListenerNotFoundError):
            find_https_listener(boto_mock, "test-application", "development")

    @patch("dbt_platform_helper.commands.environment.find_load_balancer", return_value="lb_arn")
    def test_when_https_listener_present(self, find_load_balancer):
        from dbt_platform_helper.commands.environment import find_https_listener

        boto_mock = MagicMock()
        boto_mock.client().describe_listeners.return_value = {
            "Listeners": [{"ListenerArn": "listener_arn", "Protocol": "HTTPS"}]
        }

        listener_arn = find_https_listener(boto_mock, "test-application", "development")
        assert "listener_arn" == listener_arn


class TestGetMaintenancePage:
    def test_when_environment_online(self):
        from dbt_platform_helper.commands.environment import get_maintenance_page

        boto_mock = MagicMock()
        boto_mock.client().describe_rules.return_value = {"Rules": [{"RuleArn": "rule_arn"}]}
        boto_mock.client().describe_tags.return_value = {
            "TagDescriptions": [{"ResourceArn": "rule_arn", "Tags": []}]
        }

        maintenance_page = get_maintenance_page(boto_mock, "listener_arn")
        assert maintenance_page is None

    def test_when_environment_offline_with_default_page(self):
        from dbt_platform_helper.commands.environment import get_maintenance_page

        boto_mock = MagicMock()
        boto_mock.client().describe_rules.return_value = {"Rules": [{"RuleArn": "rule_arn"}]}
        boto_mock.client().describe_tags.return_value = {
            "TagDescriptions": [
                {
                    "ResourceArn": "rule_arn",
                    "Tags": [
                        {"Key": "name", "Value": "MaintenancePage"},
                        {"Key": "type", "Value": "default"},
                    ],
                }
            ]
        }

        maintenance_page = get_maintenance_page(boto_mock, "listener_arn")
        assert maintenance_page == "default"


class TestRemoveMaintenancePage:
    def test_when_environment_online(self):
        from dbt_platform_helper.commands.environment import ListenerRuleNotFoundError
        from dbt_platform_helper.commands.environment import remove_maintenance_page

        boto_mock = MagicMock()
        boto_mock.client().describe_rules.return_value = {"Rules": [{"RuleArn": "rule_arn"}]}
        boto_mock.client().describe_tags.return_value = {
            "TagDescriptions": [{"ResourceArn": "rule_arn", "Tags": []}]
        }

        with pytest.raises(ListenerRuleNotFoundError):
            remove_maintenance_page(boto_mock, "listener_arn")

    def test_when_environment_offline(self):
        from dbt_platform_helper.commands.environment import remove_maintenance_page

        boto_mock = MagicMock()
        boto_mock.client().describe_rules.return_value = {
            "Rules": [{"RuleArn": "rule_arn"}, {"RuleArn": "allowed_ips_rule_arn"}]
        }
        boto_mock.client().describe_tags.return_value = {
            "TagDescriptions": [
                {
                    "ResourceArn": "rule_arn",
                    "Tags": [
                        {"Key": "name", "Value": "MaintenancePage"},
                        {"Key": "type", "Value": "default"},
                    ],
                },
                {
                    "ResourceArn": "allowed_ips_rule_arn",
                    "Tags": [
                        {"Key": "name", "Value": "AllowedIps"},
                        {"Key": "type", "Value": "default"},
                    ],
                },
            ]
        }
        boto_mock.client().delete_rule.return_value = None

        remove_maintenance_page(boto_mock, "listener_arn")


class TestAddMaintenancePage:
    @pytest.mark.parametrize("template", ["default", "migration", "dmas-migration"])
    @patch("dbt_platform_helper.commands.environment.random.choices", return_value=["a", "b", "c"])
    @patch("dbt_platform_helper.commands.environment.create_header_rule")
    @patch("dbt_platform_helper.commands.environment.find_target_group")
    @patch("dbt_platform_helper.commands.environment.get_maintenance_page_template")
    def test_adding_existing_template(
        self,
        get_maintenance_page_template,
        find_target_group,
        create_header_rule,
        choices,
        template,
        mock_application,
    ):
        from dbt_platform_helper.commands.environment import add_maintenance_page

        boto_mock = MagicMock()
        get_maintenance_page_template.return_value = template
        find_target_group.return_value = "target_group_arn"

        add_maintenance_page(
            boto_mock,
            "listener_arn",
            "test-application",
            "development",
            [mock_application.services["web"]],
            [],
            template,
        )

        assert create_header_rule.call_count == 1
        create_header_rule.assert_has_calls(
            [
                call(
                    boto_mock.client(),
                    "listener_arn",
                    "target_group_arn",
                    "Bypass-Key",
                    ["abc"],
                    "BypassIpFilter",
                    1,
                ),
            ]
        )
        boto_mock.client().create_rule.assert_called_once_with(
            ListenerArn="listener_arn",
            Priority=700,
            Conditions=[
                {
                    "Field": "path-pattern",
                    "PathPatternConfig": {"Values": ["/*"]},
                }
            ],
            Actions=[
                {
                    "Type": "fixed-response",
                    "FixedResponseConfig": {
                        "StatusCode": "503",
                        "ContentType": "text/html",
                        "MessageBody": template,
                    },
                }
            ],
            Tags=[
                {"Key": "name", "Value": "MaintenancePage"},
                {"Key": "type", "Value": template},
            ],
        )


class TestEnvironmentMaintenanceTemplates:
    @pytest.mark.parametrize("template", ["default", "migration", "dmas-migration"])
    def test_template_length(self, template):
        from dbt_platform_helper.commands.environment import (
            get_maintenance_page_template,
        )

        contents = get_maintenance_page_template(template)
        assert len(contents) <= 1024

    @pytest.mark.parametrize("template", ["default", "migration", "dmas-migration"])
    def test_template_no_new_lines(self, template):
        from dbt_platform_helper.commands.environment import (
            get_maintenance_page_template,
        )

        contents = get_maintenance_page_template(template)
        assert "\n" not in contents


class TestCommandHelperMethods:
    @patch("dbt_platform_helper.commands.environment.load_application")
    def test_get_app_environment(self, mock_load_application):
        from dbt_platform_helper.commands.environment import get_app_environment
        from dbt_platform_helper.utils.application import Application

        development = Mock()
        application = Application(name="test-application")
        application.environments = {"development": development}
        mock_load_application.return_value = application

        app_environment = get_app_environment("test-application", "development")

        assert app_environment == development

    @patch("dbt_platform_helper.commands.environment.load_application")
    def test_get_app_environment_does_not_exist(self, mock_load_application, capsys):
        from dbt_platform_helper.commands.environment import get_app_environment
        from dbt_platform_helper.utils.application import Application

        CliRunner()
        application = Application(name="test-application")
        mock_load_application.return_value = application

        with pytest.raises(click.Abort):
            get_app_environment("test-application", "development")

        captured = capsys.readouterr()

        assert (
            "The environment development was not found in the application test-application."
            in captured.out
        )

    def _create_subnet(self, session):
        ec2 = session.client("ec2")
        vpc_id = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]

        return (
            vpc_id,
            ec2.create_subnet(VpcId=vpc_id, CidrBlock="10.0.1.0/24")["Subnet"]["SubnetId"],
        )

    def _create_listener(self, elbv2_client):
        _, subnet_id = self._create_subnet(boto3.Session())
        load_balancer_arn = elbv2_client.create_load_balancer(
            Name="test-load-balancer", Subnets=[subnet_id]
        )["LoadBalancers"][0]["LoadBalancerArn"]
        return elbv2_client.create_listener(
            LoadBalancerArn=load_balancer_arn, DefaultActions=[{"Type": "forward"}]
        )["Listeners"][0]["ListenerArn"]

    def _create_listener_rule(self):
        elbv2_client = boto3.client("elbv2")
        listener_arn = self._create_listener(elbv2_client)
        rule_response = elbv2_client.create_rule(
            ListenerArn=listener_arn,
            Tags=[{"Key": "test-key", "Value": "test-value"}],
            Conditions=[{"Field": "path-pattern", "PathPatternConfig": {"Values": ["/test-path"]}}],
            Priority=1,
            Actions=[
                {
                    "Type": "fixed-response",
                    "FixedResponseConfig": {
                        "MessageBody": "test response",
                        "StatusCode": "200",
                        "ContentType": "text/plain",
                    },
                }
            ],
        )

        return rule_response["Rules"][0]["RuleArn"], elbv2_client, listener_arn

    def _create_target_group(self):
        ec2_client = boto3.client("ec2")
        vpc_response = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")
        vpc_id = vpc_response["Vpc"]["VpcId"]

        return boto3.client("elbv2").create_target_group(
            Name="test-target-group",
            Protocol="HTTPS",
            Port=123,
            VpcId=vpc_id,
            Tags=[
                {"Key": "copilot-application", "Value": "test-application"},
                {"Key": "copilot-environment", "Value": "development"},
                {"Key": "copilot-service", "Value": "web"},
            ],
        )["TargetGroups"][0]["TargetGroupArn"]

    @mock_aws
    def test_get_listener_rule_by_tag(self):
        from dbt_platform_helper.commands.environment import get_listener_rule_by_tag

        rule_arn, elbv2_client, listener_arn = self._create_listener_rule()

        rule = get_listener_rule_by_tag(elbv2_client, listener_arn, "test-key", "test-value")

        assert rule["RuleArn"] == rule_arn

    @mock_aws
    def test_find_target_group(self):
        from dbt_platform_helper.commands.environment import find_target_group

        target_group_arn = self._create_target_group()

        assert (
            find_target_group("test-application", "development", "web", boto3.session.Session())
            == target_group_arn
        )

    @mock_aws
    def test_find_target_group_not_found(self):
        from dbt_platform_helper.commands.environment import find_target_group

        assert (
            find_target_group("test-application", "development", "web", boto3.session.Session())
            is None
        )

    @mock_aws
    def test_delete_listener_rule(self):
        from dbt_platform_helper.commands.environment import delete_listener_rule

        rule_arn, elbv2_client, listener_arn = self._create_listener_rule()
        rules = [{"ResourceArn": rule_arn, "Tags": [{"Key": "name", "Value": "test-tag"}]}]

        described_rules = elbv2_client.describe_rules(ListenerArn=listener_arn)["Rules"]

        # sanity check that default and newly created rule both exist
        assert len(described_rules) == 2

        delete_listener_rule(rules, "test-tag", elbv2_client)

        rules = elbv2_client.describe_rules(ListenerArn=listener_arn)["Rules"]

        assert len(rules) == 1

    @mock_aws
    def test_create_header_rule(self, capsys):
        from dbt_platform_helper.commands.environment import create_header_rule

        elbv2_client = boto3.client("elbv2")
        listener_arn = self._create_listener(elbv2_client)
        target_group_arn = self._create_target_group()
        elbv2_client.create_rule(
            ListenerArn=listener_arn,
            Tags=[{"Key": "test-key", "Value": "test-value"}],
            Conditions=[{"Field": "host-header", "HostHeaderConfig": {"Values": ["/test-path"]}}],
            Priority=500,
            Actions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
        )
        rules = elbv2_client.describe_rules(ListenerArn=listener_arn)["Rules"]
        assert len(rules) == 2

        create_header_rule(
            elbv2_client,
            listener_arn,
            target_group_arn,
            "X-Forwarded-For",
            ["1.2.3.4", "5.6.7.8"],
            "AllowedIps",
            333,
        )

        rules = elbv2_client.describe_rules(ListenerArn=listener_arn)["Rules"]
        assert len(rules) == 3  # 1 default + 1 forward + 1 newly created
        assert rules[1]["Conditions"][0]["HttpHeaderConfig"]["Values"], ["1.2.3.4", "5.6.7.8"]
        assert rules[1]["Priority"] == "333"

        captured = capsys.readouterr()

        assert (
            f"Creating listener rule AllowedIps for HTTPS Listener with arn {listener_arn}.\n\nIf request header X-Forwarded-For contains one of the values ['1.2.3.4', '5.6.7.8'], the request will be forwarded to target group with arn {target_group_arn}."
            in captured.out
        )

    @pytest.mark.parametrize(
        "vpc, param_value, expected",
        [
            (
                "vpc1",
                "192.168.1.1,192.168.1.2,192.168.1.3",
                ["192.168.1.1", "192.168.1.2", "192.168.1.3"],
            ),
            (
                "vpc2",
                " 192.168.2.1 , 192.168.2.2 , 192.168.2.3 ",
                ["192.168.2.1", "192.168.2.2", "192.168.2.3"],
            ),
            (
                None,
                "192.168.1.1,192.168.1.2,192.168.1.3",
                ["192.168.1.1", "192.168.1.2", "192.168.1.3"],
            ),
        ],
    )
    @mock_aws
    def test_get_env_ips(self, vpc, param_value, expected, mock_application):
        from dbt_platform_helper.commands.environment import get_env_ips

        response = boto3.client("organizations").create_organization(FeatureSet="ALL")
        response["Organization"]["Id"]
        create_account_response = boto3.client("organizations").create_account(
            Email="test-email@example.com", AccountName="test"
        )
        account_id = create_account_response["CreateAccountStatus"]["AccountId"]
        mock_application.environments["development"].account_id = account_id
        mock_application.environments["development"].sessions[account_id] = boto3.session.Session()
        vpc = vpc if vpc else "test"
        boto3.client("ssm").put_parameter(
            Name=f"/{vpc}/EGRESS_IPS", Value=param_value, Type="String"
        )
        environment = mock_application.environments["development"]
        result = get_env_ips(vpc, environment)

        assert result == expected

    @mock_aws
    def test_get_env_ips_param_not_found(self, capsys, mock_application):
        from dbt_platform_helper.commands.environment import get_env_ips

        response = boto3.client("organizations").create_organization(FeatureSet="ALL")
        response["Organization"]["Id"]
        create_account_response = boto3.client("organizations").create_account(
            Email="test-email@example.com", AccountName="test"
        )
        account_id = create_account_response["CreateAccountStatus"]["AccountId"]
        mock_application.environments["development"].account_id = account_id
        mock_application.environments["development"].sessions[account_id] = boto3.session.Session()
        environment = mock_application.environments["development"]

        with pytest.raises(click.Abort):
            get_env_ips("vpc", environment)

        captured = capsys.readouterr()

        assert "No parameter found with name: /vpc/EGRESS_IPS\n" in captured.out

    @patch("boto3.client")
    def test_get_rules_tag_descriptions(self, mock_boto_client):
        from dbt_platform_helper.commands.environment import get_rules_tag_descriptions

        mock_client = Mock()
        mock_client.describe_tags.side_effect = [
            {"TagDescriptions": ["TagDescriptions1"]},
            {"TagDescriptions": ["TagDescriptions2"]},
        ]

        mock_boto_client.return_value = mock_client

        rules = []

        for i in range(21):
            rules.append({"RuleArn": i})

        tag_descriptions = get_rules_tag_descriptions(rules, boto3.client("elbv2"))

        assert tag_descriptions == ["TagDescriptions1", "TagDescriptions2"]
        assert mock_client.describe_tags.call_count == 2
