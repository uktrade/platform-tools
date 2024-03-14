from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from click.testing import CliRunner


class TestEnvironmentOfflineCommand:
    @patch(
        "dbt_platform_helper.commands.environment.find_https_listener",
        return_value="https_listener",
    )
    @patch("dbt_platform_helper.commands.environment.get_maintenance_page", return_value=None)
    @patch("dbt_platform_helper.commands.environment.add_maintenance_page", return_value=None)
    def test_successful_offline(
        self, add_maintenance_page, get_maintenance_page, find_https_listener, mock_application
    ):
        from dbt_platform_helper.commands.environment import offline

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
        add_maintenance_page.assert_called_with(ANY, "https_listener", "default")

        assert (
            "Maintenance page 'default' added for environment development in "
            "application test-application"
        ) in result.output

    @patch(
        "dbt_platform_helper.commands.environment.find_https_listener",
        return_value="https_listener",
    )
    @patch("dbt_platform_helper.commands.environment.get_maintenance_page", return_value=None)
    @patch("dbt_platform_helper.commands.environment.add_maintenance_page", return_value=None)
    def test_successful_offline_with_custom_template(
        self, add_maintenance_page, get_maintenance_page, find_https_listener, mock_application
    ):
        from dbt_platform_helper.commands.environment import offline

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
        add_maintenance_page.assert_called_with(ANY, "https_listener", "migration")

        assert (
            "Maintenance page 'migration' added for environment development in "
            "application test-application"
        ) in result.output

    @patch(
        "dbt_platform_helper.commands.environment.find_https_listener",
        return_value="https_listener",
    )
    @patch(
        "dbt_platform_helper.commands.environment.get_maintenance_page", return_value="maintenance"
    )
    @patch("dbt_platform_helper.commands.environment.remove_maintenance_page", return_value=None)
    @patch("dbt_platform_helper.commands.environment.add_maintenance_page", return_value=None)
    def test_successful_offline_when_already_offline(
        self,
        add_maintenance_page,
        remove_maintenance_page,
        get_maintenance_page,
        find_https_listener,
        mock_application,
    ):
        from dbt_platform_helper.commands.environment import offline

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
        add_maintenance_page.assert_called_with(ANY, "https_listener", "default")

        assert (
            "Maintenance page 'default' added for environment development in "
            "application test-application"
        ) in result.output

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
        mock_application,
    ):
        from dbt_platform_helper.commands.environment import LoadBalancerNotFoundError
        from dbt_platform_helper.commands.environment import offline

        find_https_listener.side_effect = LoadBalancerNotFoundError()

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
        mock_application,
    ):
        from dbt_platform_helper.commands.environment import ListenerNotFoundError
        from dbt_platform_helper.commands.environment import offline

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

    @patch("dbt_platform_helper.commands.environment.find_https_listener")
    @patch("dbt_platform_helper.commands.environment.get_maintenance_page")
    @patch("dbt_platform_helper.commands.environment.remove_maintenance_page")
    @patch("dbt_platform_helper.commands.environment.add_maintenance_page")
    def test_offline_an_environment_when_https_listener_not_found(
        self,
        add_maintenance_page,
        remove_maintenance_page,
        get_maintenance_page,
        find_https_listener,
        mock_application,
    ):
        from dbt_platform_helper.commands.environment import LoadBalancerNotFoundError
        from dbt_platform_helper.commands.environment import online

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
        add_maintenance_page.assert_not_called()


class TestEnvironmentOnlineCommand:
    @patch(
        "dbt_platform_helper.commands.environment.find_https_listener",
        return_value="https_listener",
    )
    @patch("dbt_platform_helper.commands.environment.get_maintenance_page", return_value="default")
    @patch("dbt_platform_helper.commands.environment.remove_maintenance_page", return_value=None)
    def test_successful_online(
        self, remove_maintenance_page, get_maintenance_page, find_https_listener, mock_application
    ):
        from dbt_platform_helper.commands.environment import online

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

    @patch(
        "dbt_platform_helper.commands.environment.find_https_listener",
        return_value="https_listener",
    )
    @patch("dbt_platform_helper.commands.environment.get_maintenance_page", return_value=None)
    @patch("dbt_platform_helper.commands.environment.remove_maintenance_page", return_value=None)
    def test_online_an_environment_that_is_not_offline(
        self, remove_maintenance_page, get_maintenance_page, find_https_listener, mock_application
    ):
        from dbt_platform_helper.commands.environment import online

        result = CliRunner().invoke(
            online, ["--app", "test-application", "--env", "development"], input="y\n"
        )

        assert "There is no current maintenance page to remove" in result.output

        find_https_listener.assert_called_with(ANY, "test-application", "development")
        get_maintenance_page.assert_called_with(ANY, "https_listener")
        remove_maintenance_page.assert_not_called()

    @patch("dbt_platform_helper.commands.environment.find_https_listener")
    @patch("dbt_platform_helper.commands.environment.get_maintenance_page")
    @patch("dbt_platform_helper.commands.environment.remove_maintenance_page")
    def test_online_an_environment_when_listener_not_found(
        self, remove_maintenance_page, get_maintenance_page, find_https_listener, mock_application
    ):
        from dbt_platform_helper.commands.environment import ListenerNotFoundError
        from dbt_platform_helper.commands.environment import online

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

    @patch("dbt_platform_helper.commands.environment.find_https_listener")
    @patch("dbt_platform_helper.commands.environment.get_maintenance_page")
    @patch("dbt_platform_helper.commands.environment.remove_maintenance_page")
    def test_online_an_environment_when_load_balancer_not_found(
        self, remove_maintenance_page, get_maintenance_page, find_https_listener, mock_application
    ):
        from dbt_platform_helper.commands.environment import LoadBalancerNotFoundError
        from dbt_platform_helper.commands.environment import online

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
        boto_mock.client().delete_rule.return_value = None

        remove_maintenance_page(boto_mock, "listener_arn")


class TestAddMaintenancePage:
    @pytest.mark.parametrize("template", ["default", "migration"])
    @patch("dbt_platform_helper.commands.environment.get_maintenance_page_template")
    def test_adding_existing_template(self, get_maintenance_page_template, template):
        from dbt_platform_helper.commands.environment import add_maintenance_page

        boto_mock = MagicMock()
        get_maintenance_page_template.return_value = template

        add_maintenance_page(boto_mock, "listener_arn", template)

        boto_mock.client().create_rule.assert_called_with(
            ListenerArn="listener_arn",
            Priority=1,
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
    @pytest.mark.parametrize("template", ["default", "migration"])
    def test_template_length(self, template):
        from dbt_platform_helper.commands.environment import (
            get_maintenance_page_template,
        )

        contents = get_maintenance_page_template(template)
        assert len(contents) <= 1024

    @pytest.mark.parametrize("template", ["default", "migration"])
    def test_template_no_new_lines(self, template):
        from dbt_platform_helper.commands.environment import (
            get_maintenance_page_template,
        )

        contents = get_maintenance_page_template(template)
        assert "\n" not in contents
