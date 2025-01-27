from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import call
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from dbt_platform_helper.domain.maintenance_page import *
from dbt_platform_helper.utils.application import Application

app = "test-application"
env = "development"
svc = ["web"]
template = "default"
vpc = None


class TestGetMaintenancePage:
    def test_when_environment_online(self):

        boto_mock = MagicMock()
        boto_mock.client().describe_rules.return_value = {"Rules": [{"RuleArn": "rule_arn"}]}
        boto_mock.client().describe_tags.return_value = {
            "TagDescriptions": [{"ResourceArn": "rule_arn", "Tags": []}]
        }

        maintenance_page = get_maintenance_page_type(boto_mock, "listener_arn")
        assert maintenance_page is None

    def test_when_environment_offline_with_default_page(self):

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

        maintenance_page = get_maintenance_page_type(boto_mock, "listener_arn")
        assert maintenance_page == "default"


class TestRemoveMaintenancePage:
    def test_when_environment_online(self):

        boto_mock = MagicMock()
        boto_mock.client().describe_rules.return_value = {"Rules": [{"RuleArn": "rule_arn"}]}
        boto_mock.client().describe_tags.return_value = {
            "TagDescriptions": [{"ResourceArn": "rule_arn", "Tags": []}]
        }

        with pytest.raises(ListenerRuleNotFoundException):
            remove_maintenance_page(boto_mock, "listener_arn")

    @patch("dbt_platform_helper.domain.maintenance_page.delete_listener_rule")
    def test_when_environment_offline(self, delete_listener_rule):

        boto_mock = MagicMock()
        boto_mock.client().describe_rules.return_value = {
            "Rules": [{"RuleArn": "rule_arn"}, {"RuleArn": "allowed_ips_rule_arn"}]
        }
        tag_descriptions = [
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
            {
                "ResourceArn": "allowed_source_ips_rule_arn",
                "Tags": [
                    {"Key": "name", "Value": "AllowedSourceIps"},
                    {"Key": "type", "Value": "default"},
                ],
            },
        ]
        boto_mock.client().describe_tags.return_value = {"TagDescriptions": tag_descriptions}
        boto_mock.client().delete_rule.return_value = None

        remove_maintenance_page(boto_mock, "listener_arn")

        delete_listener_rule.assert_has_calls(
            [
                call(tag_descriptions, "MaintenancePage", boto_mock.client()),
                call().__bool__(),  # return value of mock is referenced in line: `if name == "MaintenancePage" and not deleted`
                call(tag_descriptions, "AllowedIps", boto_mock.client()),
                call(tag_descriptions, "BypassIpFilter", boto_mock.client()),
                call(tag_descriptions, "AllowedSourceIps", boto_mock.client()),
            ]
        )


class TestAddMaintenancePage:
    @pytest.mark.parametrize("template", ["default", "migration", "dmas-migration"])
    @patch(
        "dbt_platform_helper.domain.maintenance_page.random.choices", return_value=["a", "b", "c"]
    )
    @patch("dbt_platform_helper.domain.maintenance_page.create_source_ip_rule")
    @patch("dbt_platform_helper.domain.maintenance_page.create_header_rule")
    @patch("dbt_platform_helper.domain.maintenance_page.find_target_group")
    @patch("dbt_platform_helper.domain.maintenance_page.get_maintenance_page_template")
    def test_adding_existing_template(
        self,
        get_maintenance_page_template,
        find_target_group,
        create_header_rule,
        create_source_ip,
        choices,
        template,
        mock_application,
    ):

        boto_mock = MagicMock()
        get_maintenance_page_template.return_value = template
        find_target_group.return_value = "target_group_arn"

        add_maintenance_page(
            boto_mock,
            "listener_arn",
            "test-application",
            "development",
            [mock_application.services["web"]],
            ["1.2.3.4"],
            template,
        )

        assert create_header_rule.call_count == 2
        create_header_rule.assert_has_calls(
            [
                call(
                    boto_mock.client(),
                    "listener_arn",
                    "target_group_arn",
                    "X-Forwarded-For",
                    ["1.2.3.4"],
                    "AllowedIps",
                    1,
                ),
                call(
                    boto_mock.client(),
                    "listener_arn",
                    "target_group_arn",
                    "Bypass-Key",
                    ["abc"],
                    "BypassIpFilter",
                    3,
                ),
            ]
        )
        create_source_ip.assert_has_calls(
            [
                call(
                    boto_mock.client(),
                    "listener_arn",
                    "target_group_arn",
                    ["1.2.3.4"],
                    "AllowedSourceIps",
                    2,
                )
            ]
        )
        boto_mock.client().create_rule.assert_called_once_with(
            ListenerArn="listener_arn",
            Priority=4,
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

        contents = get_maintenance_page_template(template)
        assert len(contents) <= 1024

    @pytest.mark.parametrize("template", ["default", "migration", "dmas-migration"])
    def test_template_no_new_lines(self, template):

        contents = get_maintenance_page_template(template)
        assert "\n" not in contents


class TestCommandHelperMethods:
    def test_get_app_environment(self):

        development = Mock()
        application = Application(name="test-application")
        application.environments = {"development": development}

        app_environment = get_app_environment(application, "development")

        assert app_environment == development

    def test_get_app_environment_does_not_exist(self, capsys):

        application = Application(name="test-application")

        with pytest.raises(click.Abort):
            get_app_environment(application, "development")

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

    def _create_listener_rule(self, elbv2_client=None, listener_arn=None, priority=1):
        if not elbv2_client:
            elbv2_client = boto3.client("elbv2")

        if not listener_arn:
            listener_arn = self._create_listener(elbv2_client)

        rule_response = elbv2_client.create_rule(
            ListenerArn=listener_arn,
            Tags=[{"Key": "test-key", "Value": "test-value"}],
            Conditions=[{"Field": "path-pattern", "PathPatternConfig": {"Values": ["/test-path"]}}],
            Priority=priority,
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
    def test_find_target_group(self):

        target_group_arn = self._create_target_group()

        assert (
            find_target_group("test-application", "development", "web", boto3.session.Session())
            == target_group_arn
        )

    @mock_aws
    def test_find_target_group_not_found(self):

        assert (
            find_target_group("test-application", "development", "web", boto3.session.Session())
            is None
        )

    @mock_aws
    def test_delete_listener_rule(self):

        rule_arn, elbv2_client, listener_arn = self._create_listener_rule()
        rule_2_arn, _, _ = self._create_listener_rule(
            priority=2, elbv2_client=elbv2_client, listener_arn=listener_arn
        )
        rules = [
            {"ResourceArn": rule_arn, "Tags": [{"Key": "name", "Value": "test-tag"}]},
            {"ResourceArn": rule_2_arn, "Tags": [{"Key": "name", "Value": "test-tag"}]},
        ]

        described_rules = elbv2_client.describe_rules(ListenerArn=listener_arn)["Rules"]

        # sanity check that default and two newly created rules  exist
        assert len(described_rules) == 3

        delete_listener_rule(rules, "test-tag", elbv2_client)

        rules = elbv2_client.describe_rules(ListenerArn=listener_arn)["Rules"]

        assert len(rules) == 1

    @mock_aws
    def test_create_header_rule(self, capsys):

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
        "allowed_ips, expected_rule_cidr",
        [
            (
                ["1.2.3.4", "5.6.7.8"],
                ["1.2.3.4/32", "5.6.7.8/32"],
            ),
            (
                ["1.2.3.4/32", "5.6.7.8/24"],
                ["1.2.3.4/32", "5.6.7.8/24"],
            ),
        ],
    )
    @mock_aws
    def test_create_source_ip_rule(self, allowed_ips, expected_rule_cidr, capsys):

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

        create_source_ip_rule(
            elbv2_client,
            listener_arn,
            target_group_arn,
            allowed_ips,
            "AllowedSourceIps",
            333,
        )

        rules = elbv2_client.describe_rules(ListenerArn=listener_arn)["Rules"]
        assert len(rules) == 3  # 1 default + 1 forward + 1 newly created
        assert sorted(rules[1]["Conditions"][0]["SourceIpConfig"]["Values"]) == sorted(
            expected_rule_cidr
        )
        assert rules[1]["Priority"] == "333"

        captured = capsys.readouterr()

        assert (
            f"Creating listener rule AllowedSourceIps for HTTPS Listener with arn {listener_arn}.\n\nIf request source ip matches one of the values {allowed_ips}, the request will be forwarded to target group with arn {target_group_arn}."
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
                "vpc1",
                "192.168.1.1/32",
                ["192.168.1.1/32"],
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

    @pytest.mark.parametrize(
        "ip, expected_cidr",
        [
            (
                "1.2.3.4",
                "1.2.3.4/32",
            ),
            (
                "1.2.3.4/32",
                "1.2.3.4/32",
            ),
            (
                "1.2.3.4/128",
                "1.2.3.4/128",
            ),
        ],
    )
    def test_normalise_to_cidr(self, ip, expected_cidr):
        assert normalise_to_cidr(ip) == expected_cidr

    @mock_aws
    @patch(
        "dbt_platform_helper.domain.maintenance_page.random.choices", return_value=["a", "b", "c"]
    )
    @patch("dbt_platform_helper.domain.maintenance_page.get_maintenance_page_template")
    def test_listener_roll_back_on_exception(
        self, get_maintenance_page_template, choices, mock_application
    ):

        get_maintenance_page_template.return_value = "default"

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

        original_create_rule = elbv2_client.create_rule

        def mock_create_rule(*args, **kwargs):
            if mock_create_rule.call_count == 1:
                mock_create_rule.call_count += 1
                raise ClientError(
                    {"Error": {"Code": "ValidationError", "Message": "Simulated failure"}},
                    "CreateRule",
                )
            mock_create_rule.call_count += 1
            return original_create_rule(*args, **kwargs)

        mock_create_rule.call_count = 0

        elbv2_client.create_rule = mock_create_rule

        mock_session = MagicMock()

        def mock_client(service_name, **kwargs):
            # TODO for service_name try get from kwargs["mocks"] else default
            if service_name == "elbv2":
                return elbv2_client
            elif service_name == "resourcegroupstaggingapi":
                return boto3.client("resourcegroupstaggingapi")

        mock_session.client.side_effect = mock_client

        with pytest.raises(FailedToActivateMaintenancePageException, match=""):
            add_maintenance_page(
                mock_session,
                listener_arn,
                "test-application",
                "development",
                [mock_application.services["web"]],
                ["1.2.3.4"],
                template,
            )

            assert mock_create_rule.call_count == 2

            rules = elbv2_client.describe_rules(ListenerArn=listener_arn)["Rules"]
            tags_descriptions = elbv2_client.describe_tags(
                ResourceArns=[rule["RuleArn"] for rule in rules]
            )

            # check that it only contains test tag and not maintenance page tags. Note default rule has no tags
            for description in tags_descriptions["TagDescriptions"]:
                tags = {t["Key"]: t["Value"] for t in description["Tags"]}
                assert tags.get("name", None) not in [
                    "MaintenancePage",
                    "AllowedIps",
                    "BypassIpFilter",
                    "AllowedSourceIps",
                ]

                if tags.get("test-key"):
                    assert tags["test-key"] == "test-value"

            # check it doesn't contain any maintenance page rules
            for rule in rules:
                for conidition in rule["Conditions"]:
                    assert conidition not in [
                        {
                            "Field": "http-header",
                            "HttpHeaderConfig": {
                                "HttpHeaderName": "X-Forwarded-For",
                                "Values": ["1.2.3.4"],
                            },
                        },
                        {"Field": "source-ip", "SourceIpConfig": {"Values": ["1.2.3.4/32"]}},
                        {
                            "Field": "http-header",
                            "HttpHeaderConfig": {"HttpHeaderName": "Bypass-Key", "Values": ["abc"]},
                        },
                        {"Field": "path-pattern", "PathPatternConfig": {"Values": ["/*"]}},
                    ]
                assert rule["Priority"] not in ["1", "2", "3", "4"]

            assert len(rules) == 2


class MaintenancePageMocks:
    def __init__(self, app_name="test-application", *args, **kwargs):
        session = Mock()
        sessions = {"000000000": session}
        dummy_application = Application(app_name)
        dummy_application.environments = {env: Environment(env, "000000000", sessions)}
        dummy_application.services = {"web": Service("web", "Load Balanced Web Service")}
        self.application = dummy_application

        self.get_https_listener_for_application = kwargs.get(
            "get_https_listener_for_application", Mock(return_value="https_listener")
        )
        self.io = kwargs.get("io", Mock())
        self.io.confirm = Mock(return_value="yes")
        self.io.abort_with_error = Mock(side_effect=SystemExit(1))
        self.get_maintenance_page_type = kwargs.get(
            "get_maintenance_page_type", Mock(return_value=None)
        )
        self.get_env_ips = kwargs.get("get_env_ips", Mock(return_value=["0.1.2.3, 4.5.6.7"]))
        self.add_maintenance_page = kwargs.get("add_maintenance_page", Mock(return_value=None))
        self.remove_maintenance_page = kwargs.get(
            "remove_maintenance_page", Mock(return_value=None)
        )

    def params(self):
        return {
            "application": self.application,
            "get_https_listener_for_application": self.get_https_listener_for_application,
            "io": self.io,
            "get_maintenance_page_type": self.get_maintenance_page_type,
            "get_env_ips": self.get_env_ips,
            "add_maintenance_page": self.add_maintenance_page,
            "remove_maintenance_page": self.remove_maintenance_page,
        }


class TestActivateMethod:

    def test_successful_activate(
        self,
    ):

        maintenance_mocks = MaintenancePageMocks(app)
        provider = MaintenancePage(**maintenance_mocks.params())
        provider.activate(env, svc, template, vpc)

        maintenance_mocks.get_https_listener_for_application.assert_called_with(
            ANY, "test-application", "development"
        )
        maintenance_mocks.get_maintenance_page_type.assert_called_with(ANY, "https_listener")
        maintenance_mocks.get_env_ips.assert_called_with(
            vpc, maintenance_mocks.application.environments["development"]
        )
        maintenance_mocks.add_maintenance_page.assert_called_with(
            ANY,
            "https_listener",
            "test-application",
            "development",
            [maintenance_mocks.application.services["web"]],
            ["0.1.2.3, 4.5.6.7"],
            "default",
        )

        maintenance_mocks.io.confirm.assert_has_calls(
            [
                call(
                    "You are about to enable the 'default' maintenance page for the development "
                    "environment in test-application.\nWould you like to continue?"
                ),
            ]
        )
        maintenance_mocks.io.info.assert_called_with(
            "Maintenance page 'default' added for environment development in "
            "application test-application",
        )

    def test_successful_activate_with_custom_template(
        self,
    ):
        template = "migration"
        maintenance_mocks = MaintenancePageMocks(app)
        provider = MaintenancePage(**maintenance_mocks.params())
        provider.activate(env, svc, template, vpc)

        maintenance_mocks.get_https_listener_for_application.assert_called_with(
            ANY, "test-application", "development"
        )
        maintenance_mocks.get_maintenance_page_type.assert_called_with(ANY, "https_listener")
        maintenance_mocks.get_env_ips.assert_called_with(
            vpc, maintenance_mocks.application.environments["development"]
        )
        maintenance_mocks.add_maintenance_page.assert_called_with(
            ANY,
            "https_listener",
            "test-application",
            "development",
            [maintenance_mocks.application.services["web"]],
            ["0.1.2.3, 4.5.6.7"],
            "migration",
        )

        maintenance_mocks.io.confirm.assert_has_calls(
            [
                call(
                    "You are about to enable the 'migration' maintenance page for the development "
                    "environment in test-application.\nWould you like to continue?"
                ),
            ]
        )
        maintenance_mocks.io.info.assert_called_with(
            "Maintenance page 'migration' added for environment development in "
            "application test-application",
        )

    def test_successful_activate_when_already_activated(
        self,
    ):

        maintenance_mocks = MaintenancePageMocks(
            app, get_maintenance_page_type=Mock(return_value="maintenance")
        )
        provider = MaintenancePage(**maintenance_mocks.params())
        provider.activate(env, svc, template, vpc)

        maintenance_mocks.get_https_listener_for_application.assert_called_with(
            ANY, "test-application", "development"
        )
        maintenance_mocks.get_maintenance_page_type.assert_called_with(ANY, "https_listener")
        maintenance_mocks.get_env_ips.assert_called_with(
            vpc, maintenance_mocks.application.environments["development"]
        )
        maintenance_mocks.add_maintenance_page.assert_called_with(
            ANY,
            "https_listener",
            "test-application",
            "development",
            [maintenance_mocks.application.services["web"]],
            ["0.1.2.3, 4.5.6.7"],
            "default",
        )

        maintenance_mocks.io.confirm.assert_has_calls(
            [
                call(
                    "There is currently a 'maintenance' maintenance page for the development "
                    "environment in test-application.\nWould you like to replace it with a 'default' maintenance page?"
                ),
            ]
        )
        maintenance_mocks.io.info.assert_called_with(
            "Maintenance page 'default' added for environment development in "
            "application test-application",
        )

        maintenance_mocks.remove_maintenance_page.assert_called_with(ANY, "https_listener")

    def test_activate_do_not_replace_template(self):
        maintenance_mocks = MaintenancePageMocks(
            app, get_maintenance_page_type=Mock(return_value="maintenance")
        )
        maintenance_mocks.io.confirm.return_value = False
        provider = MaintenancePage(**maintenance_mocks.params())
        provider.activate(env, svc, template, vpc)

        maintenance_mocks.get_https_listener_for_application.assert_called_with(
            ANY, "test-application", "development"
        )
        maintenance_mocks.get_maintenance_page_type.assert_called_with(ANY, "https_listener")
        maintenance_mocks.io.confirm.assert_has_calls(
            [
                call(
                    "There is currently a 'maintenance' maintenance page for the development "
                    "environment in test-application.\nWould you like to replace it with a 'default' maintenance page?"
                ),
            ]
        )

        maintenance_mocks.get_env_ips.assert_not_called()
        maintenance_mocks.add_maintenance_page.assert_not_called()
        maintenance_mocks.io.assert_not_called()
        maintenance_mocks.remove_maintenance_page.assert_not_called()

    def test_activate_do_not_enable_page(self):
        maintenance_mocks = MaintenancePageMocks(
            app,
        )
        maintenance_mocks.io.confirm.return_value = False
        provider = MaintenancePage(**maintenance_mocks.params())

        provider.activate(env, svc, template, vpc)

        maintenance_mocks.get_https_listener_for_application.assert_called_with(
            ANY, "test-application", "development"
        )
        maintenance_mocks.get_maintenance_page_type.assert_called_with(ANY, "https_listener")
        maintenance_mocks.io.confirm.assert_has_calls(
            [
                call(
                    "You are about to enable the 'default' maintenance page for the development "
                    "environment in test-application.\nWould you like to continue?"
                ),
            ]
        )

        maintenance_mocks.get_env_ips.assert_not_called()
        maintenance_mocks.add_maintenance_page.assert_not_called()
        maintenance_mocks.remove_maintenance_page.assert_not_called()

    # TODO this doesn't need to be caught in maintenance domain
    def test_activate_page_when_load_balancer_not_found(
        self,
    ):

        maintenance_mocks = MaintenancePageMocks(
            app,
            get_https_listener_for_application=Mock(side_effect=LoadBalancerNotFoundException()),
        )
        provider = MaintenancePage(**maintenance_mocks.params())

        with pytest.raises(SystemExit):
            provider.activate(env, svc, template, vpc)

        maintenance_mocks.get_https_listener_for_application.assert_called_with(
            ANY, "test-application", "development"
        )
        maintenance_mocks.get_maintenance_page_type.assert_not_called()
        maintenance_mocks.remove_maintenance_page.assert_not_called()
        maintenance_mocks.io.abort_with_error.assert_called_with(
            "No load balancer found for environment development in the application "
            "test-application.",
        )

    # TODO this doesn't need to be caught in maintenance domain
    def test_activate_page_when_listener_not_found(
        self,
    ):
        maintenance_mocks = MaintenancePageMocks(
            app, get_https_listener_for_application=Mock(side_effect=ListenerNotFoundException())
        )
        provider = MaintenancePage(**maintenance_mocks.params())

        with pytest.raises(SystemExit):
            provider.activate(env, svc, template, vpc)

        maintenance_mocks.io.abort_with_error.assert_called_with(
            "No HTTPS listener found for environment development in the application "
            "test-application.",
        )
        maintenance_mocks.get_https_listener_for_application.assert_called_with(
            ANY, "test-application", "development"
        )
        maintenance_mocks.get_maintenance_page_type.assert_not_called()
        maintenance_mocks.remove_maintenance_page.assert_not_called()
        maintenance_mocks.add_maintenance_page.assert_not_called()

    def test_activate_an_environment_when_no_load_balancer_service_found(
        self,
    ):
        services = ["not-an-alb-service"]
        maintenance_mocks = MaintenancePageMocks(
            app,
        )
        maintenance_mocks.application.services["not-an-alb-service"] = Service(
            "not-an-alb-service", "Backend Service"
        )
        provider = MaintenancePage(**maintenance_mocks.params())

        with pytest.raises(
            LoadBalancedWebServiceNotFoundException,
            match="No services deployed yet to test-application",
        ):
            provider.activate(env, services, template, vpc)

            maintenance_mocks.get_https_listener_for_application.assert_not_called()
            maintenance_mocks.get_maintenance_page_type.assert_not_called()
            maintenance_mocks.remove_maintenance_page.assert_not_called()
            maintenance_mocks.add_maintenance_page.assert_not_called()

    def test_successful_activate_multiple_services(
        self,
    ):

        maintenance_mocks = MaintenancePageMocks(
            app,
        )
        maintenance_mocks.application.services["web2"] = Service(
            "web2", "Load Balanced Web Service"
        )

        services = "*"
        provider = MaintenancePage(**maintenance_mocks.params())
        provider.activate(env, services, template, vpc)

        maintenance_mocks.get_https_listener_for_application.assert_called_with(
            ANY, "test-application", "development"
        )
        maintenance_mocks.get_maintenance_page_type.assert_called_with(ANY, "https_listener")
        maintenance_mocks.get_env_ips.assert_called_with(
            vpc, maintenance_mocks.application.environments["development"]
        )
        maintenance_mocks.add_maintenance_page.assert_called_with(
            ANY,
            "https_listener",
            "test-application",
            "development",
            [
                maintenance_mocks.application.services["web"],
                maintenance_mocks.application.services["web2"],
            ],
            ["0.1.2.3, 4.5.6.7"],
            "default",
        )

        maintenance_mocks.io.confirm.assert_has_calls(
            [
                call(
                    "You are about to enable the 'default' maintenance page for the development "
                    "environment in test-application.\nWould you like to continue?"
                ),
            ]
        )
        maintenance_mocks.io.info.assert_called_with(
            "Maintenance page 'default' added for environment development in "
            "application test-application",
        )


class TestDeactivateCommand:

    def test_successful_deactivate(
        self,
    ):
        maintenance_mocks = MaintenancePageMocks(
            app, get_maintenance_page_type=Mock(return_value="default")
        )
        provider = MaintenancePage(**maintenance_mocks.params())

        provider.deactivate(env)

        maintenance_mocks.get_https_listener_for_application.assert_called_with(
            ANY, "test-application", "development"
        )
        maintenance_mocks.get_maintenance_page_type.assert_called_with(ANY, "https_listener")
        maintenance_mocks.remove_maintenance_page.assert_called_with(ANY, "https_listener")
        maintenance_mocks.io.confirm.assert_has_calls(
            [
                call(
                    "There is currently a 'default' maintenance page, would you like to remove it?"
                ),
            ]
        )
        maintenance_mocks.io.info.assert_called_with(
            "Maintenance page removed from environment development in "
            "application test-application",
        )

    def test_deactivate_an_environment_that_is_deactivated(
        self,
    ):
        maintenance_mocks = MaintenancePageMocks(
            app,
        )
        provider = MaintenancePage(**maintenance_mocks.params())

        provider.deactivate(env)

        maintenance_mocks.get_https_listener_for_application.assert_called_with(
            ANY, "test-application", "development"
        )
        maintenance_mocks.get_maintenance_page_type.assert_called_with(ANY, "https_listener")
        maintenance_mocks.remove_maintenance_page.assert_not_called()
        maintenance_mocks.io.warn.assert_called_with(
            "There is no current maintenance page to remove",
        )

    def test_deactivate_an_environment_do_not_remove_maintenance_page(
        self,
    ):
        maintenance_mocks = MaintenancePageMocks(
            app,
            get_maintenance_page_type=Mock(return_value="default"),
        )
        maintenance_mocks.io.confirm.return_value = False

        provider = MaintenancePage(**maintenance_mocks.params())

        provider.deactivate(env)

        maintenance_mocks.get_https_listener_for_application.assert_called_with(
            ANY, "test-application", "development"
        )
        maintenance_mocks.get_maintenance_page_type.assert_called_with(ANY, "https_listener")
        maintenance_mocks.io.confirm.assert_called_with(
            "There is currently a 'default' maintenance page, " "would you like to remove it?"
        )
        maintenance_mocks.remove_maintenance_page.assert_not_called()

    def test_deactivate_an_environment_when_listener_not_found(
        self,
    ):

        maintenance_mocks = MaintenancePageMocks(
            app, get_https_listener_for_application=Mock(side_effect=ListenerNotFoundException())
        )
        provider = MaintenancePage(**maintenance_mocks.params())
        with pytest.raises(SystemExit):
            provider.deactivate(env)

        maintenance_mocks.get_https_listener_for_application.assert_called_with(
            ANY, "test-application", "development"
        )
        maintenance_mocks.get_maintenance_page_type.assert_not_called()
        maintenance_mocks.remove_maintenance_page.assert_not_called()

        maintenance_mocks.io.abort_with_error.assert_called_with(
            "No HTTPS listener found for environment development in the application "
            "test-application.",
        )

    def test_deactivate_an_environment_when_load_balancer_not_found(
        self,
    ):
        maintenance_mocks = MaintenancePageMocks(
            app,
            get_https_listener_for_application=Mock(side_effect=LoadBalancerNotFoundException()),
        )
        provider = MaintenancePage(**maintenance_mocks.params())
        with pytest.raises(SystemExit):
            provider.deactivate(env)

        maintenance_mocks.get_https_listener_for_application.assert_called_with(
            ANY, "test-application", "development"
        )
        maintenance_mocks.get_maintenance_page_type.assert_not_called()
        maintenance_mocks.remove_maintenance_page.assert_not_called()
        maintenance_mocks.io.abort_with_error.assert_called_with(
            "No load balancer found for environment development in the application "
            "test-application.",
        )
