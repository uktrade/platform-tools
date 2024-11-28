from pathlib import Path
from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import boto3
import click
import pytest
import yaml
from click.testing import CliRunner
from moto import mock_aws

from dbt_platform_helper.commands.environment import CertificateNotFoundError
from dbt_platform_helper.commands.environment import find_https_certificate
from dbt_platform_helper.commands.environment import generate
from dbt_platform_helper.commands.environment import generate_terraform
from dbt_platform_helper.commands.environment import get_cert_arn
from dbt_platform_helper.commands.environment import get_subnet_ids
from dbt_platform_helper.commands.environment import get_vpc_id
from dbt_platform_helper.commands.environment import offline
from dbt_platform_helper.commands.environment import online
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.providers.load_balancers import ListenerNotFoundError
from dbt_platform_helper.providers.load_balancers import LoadBalancerNotFoundError
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
    @patch("dbt_platform_helper.commands.environment.get_aws_session_or_abort")
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
        mock_get_subnet_ids.assert_called_once_with(mocked_session, "vpc-abc123")
        mock_get_cert_arn.assert_called_once_with(mocked_session, "my-app", "test")
        mock_get_aws_session_1.assert_called_once_with("non-prod-acc")

        assert actual == expected
        assert "File copilot/environments/test/manifest.yml created" in result.output

    @patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    @patch("dbt_platform_helper.commands.environment.get_aws_session_or_abort")
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

    @patch("dbt_platform_helper.commands.environment.get_aws_session_or_abort")
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

    @pytest.mark.parametrize("vpc_name", ["default", "default-prod"])
    @mock_aws
    def test_get_vpc_id(self, vpc_name):
        session = boto3.session.Session()
        vpc = self.create_mocked_vpc(session, vpc_name)
        expected_vpc_id = vpc["VpcId"]

        actual_vpc_id = get_vpc_id(session, "prod")

        assert expected_vpc_id == actual_vpc_id

        vpc_id_from_name = get_vpc_id(session, "not-an-env", vpc_name=vpc_name)

        assert expected_vpc_id == vpc_id_from_name

    @mock_aws
    def test_get_vpc_id_failure(self, capsys):

        with pytest.raises(click.Abort):
            get_vpc_id(boto3.session.Session(), "development")

        captured = capsys.readouterr()

        assert "No VPC found with name default-development in AWS account default." in captured.out

    @mock_aws
    def test_get_subnet_ids(self):
        session = boto3.session.Session()
        vpc_id = self.create_mocked_vpc(session, "default-development")["VpcId"]
        expected_public_subnet_id = self.create_mocked_subnet(
            session, vpc_id, "public", "10.0.128.0/24"
        )
        expected_private_subnet_id = self.create_mocked_subnet(
            session, vpc_id, "private", "10.0.1.0/24"
        )

        public_subnet_ids, private_subnet_ids = get_subnet_ids(session, vpc_id)

        assert public_subnet_ids == [expected_public_subnet_id]
        assert private_subnet_ids == [expected_private_subnet_id]

    # Todo: test_get_subnet_ids_with_cloudformation_export_returning_different_subnets

    @mock_aws
    def test_get_subnet_ids_with_cloudformation_export_returning_a_different_order(self):
        expected_private_subnet_id = "subnet-ec792dd7"
        expected_public_subnet_id = "vpc-1116baee"
        mock_boto3_session = MagicMock()
        mock_boto3_session.client("ec2").describe_subnets.return_value = {
            "Subnets": [
                {
                    "SubnetId": expected_private_subnet_id,
                    "Tags": [{"Key": "subnet_type", "Value": "private"}],
                },
                {
                    "SubnetId": expected_public_subnet_id,
                    "Tags": [{"Key": "subnet_type", "Value": "public"}],
                },
            ]
        }

        public_subnet_ids, private_subnet_ids = get_subnet_ids(
            mock_boto3_session, "vpc-id-does-not-matter"
        )

        assert public_subnet_ids == [expected_public_subnet_id]
        assert private_subnet_ids == [expected_private_subnet_id]

    @mock_aws
    def test_get_subnet_ids_failure(self, capsys):

        with pytest.raises(click.Abort):
            get_subnet_ids(boto3.session.Session(), "123")

        captured = capsys.readouterr()

        assert "No subnets found for VPC with id: 123." in captured.out

    @mock_aws
    @patch(
        "dbt_platform_helper.commands.environment.find_https_certificate",
        return_value="CertificateArn",
    )
    def test_get_cert_arn(self, find_https_certificate):

        session = boto3.session.Session()
        actual_arn = get_cert_arn(session, "test-application", "development")

        assert "CertificateArn" == actual_arn

    @mock_aws
    def test_cert_arn_failure(self, capsys):

        session = boto3.session.Session()

        with pytest.raises(click.Abort):
            get_cert_arn(session, "test-application", "development")

        captured = capsys.readouterr()

        assert (
            "No certificate found with domain name matching environment development."
            in captured.out
        )

    def create_mocked_subnet(self, session, vpc_id, visibility, cidr_block):
        return session.client("ec2").create_subnet(
            CidrBlock=cidr_block,
            VpcId=vpc_id,
            TagSpecifications=[
                {
                    "ResourceType": "subnet",
                    "Tags": [
                        {"Key": "subnet_type", "Value": visibility},
                    ],
                },
            ],
        )["Subnet"]["SubnetId"]

    def create_mocked_vpc(self, session, vpc_name):
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
        return vpc


class TestFindHTTPSCertificate:
    @patch(
        "dbt_platform_helper.commands.environment.find_https_listener",
        return_value="https_listener_arn",
    )
    def test_when_no_certificate_present(self, mock_find_https_listener):
        boto_mock = MagicMock()
        boto_mock.client().describe_listener_certificates.return_value = {"Certificates": []}

        with pytest.raises(CertificateNotFoundError):
            find_https_certificate(boto_mock, "test-application", "development")

    @patch(
        "dbt_platform_helper.commands.environment.find_https_listener",
        return_value="https_listener_arn",
    )
    def test_when_single_https_certificate_present(self, mock_find_https_listener):
        boto_mock = MagicMock()
        boto_mock.client().describe_listener_certificates.return_value = {
            "Certificates": [{"CertificateArn": "certificate_arn", "IsDefault": "True"}]
        }

        certificate_arn = find_https_certificate(boto_mock, "test-application", "development")
        assert "certificate_arn" == certificate_arn

    @patch(
        "dbt_platform_helper.commands.environment.find_https_listener",
        return_value="https_listener_arn",
    )
    def test_when_multiple_https_certificate_present(self, mock_find_https_listener):
        boto_mock = MagicMock()
        boto_mock.client().describe_listener_certificates.return_value = {
            "Certificates": [
                {"CertificateArn": "certificate_arn_default", "IsDefault": "True"},
                {"CertificateArn": "certificate_arn_not_default", "IsDefault": "False"},
            ]
        }

        certificate_arn = find_https_certificate(boto_mock, "test-application", "development")
        assert "certificate_arn_default" == certificate_arn
