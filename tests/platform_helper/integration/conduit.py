import json
import os

import boto3
import pytest
from click.testing import CliRunner
from moto import mock_aws

from dbt_platform_helper.commands.conduit import conduit


# copied function
def add_addon_config_parameter(param_value=None):
    mock_ssm = boto3.client("ssm")
    mock_ssm.put_parameter(
        Name=f"/copilot/applications/test/environments/one/addons",
        Type="String",
        Value=json.dumps(
            param_value
            or {
                "fake-postgres": {"type": "postgres"},
                "custom-name-opensearch": {"type": "opensearch"},
                "custom-name-redis": {"type": "redis"},
            }
        ),
    )


"""
We can wrap integration tests with setup env
this means if USE_MOCKS is true we will not call to any real service and mock the environment 

when USE_MOCK is true it will run against the real AWS for e2e tests

this could be used to wrap all our code too so we can test locally without calling out to AWS
we could have ...
- moto configured
- custom stubs for providers
- localstack 
"""


@pytest.fixture
def setup_environment(mock_cluster_client_task, mock_stack):
    use_mocks = os.getenv("USE_MOCKS", "true").lower() == "true"
    if use_mocks:
        with mock_aws():
            ssm_client = boto3.client("ssm")
            ssm_client.put_parameter(
                Name=f"/copilot/applications/test",
                Value=json.dumps(
                    {
                        "name": "test",
                        "account": "111111111",
                    }
                ),
                Type="String",
            )
            ssm_client.put_parameter(
                Name=f"/copilot/applications/test/environments/one",
                Value=json.dumps(
                    {
                        "name": "one",
                        "accountID": "111111111",
                    }
                ),
                Type="String",
            )
            ssm_client.put_parameter(
                Name=f"/copilot/applications/test/environments/two",
                Value=json.dumps(
                    {
                        "name": "two",
                        "accountID": "222222222",
                    }
                ),
                Type="String",
            )
            mock_secretsmanager = boto3.client("secretsmanager")
            secret_name = "/copilot/test/one/secrets/FAKE_POSTGRES"
            add_addon_config_parameter()
            mock_secretsmanager.create_secret(
                Name=secret_name + "_READ_ONLY_USER",
                SecretString="not-a-real-secret",
            )
            ssm_client.put_parameter(
                Name=secret_name,
                Value="something-secret",
                Type="SecureString",
            )

            boto3.client("ecs").create_cluster(
                tags=[
                    {"key": "copilot-application", "value": "test"},
                    {"key": "copilot-environment", "value": "one"},
                    {"key": "aws:cloudformation:logical-id", "value": "Cluster"},
                ]
            )

            mock_cluster_client_task("postgres")

            boto3.client("iam").create_role(
                RoleName="CWLtoSubscriptionFilterRole",
                AssumeRolePolicyDocument="123",
            )
            boto3.client("iam").create_role(
                RoleName="fake-postgres-test-one-conduitEcsTask",
                AssumeRolePolicyDocument="123",
            )

            ssm_response = {
                "prod": "arn:aws:logs:eu-west-2:prod_account_id:destination:test_log_destination",
                "dev": "arn:aws:logs:eu-west-2:dev_account_id:destination:test_log_destination",
            }
            boto3.client("ssm").put_parameter(
                Name="/copilot/tools/central_log_groups",
                Value=json.dumps(ssm_response),
                Type="String",
            )

            mock_stack("fake-postgres")

            yield
    else:
        yield


from unittest.mock import patch
from unittest.mock import call

"""
Due to a few bugs escaping until e2e tests or manually testing is done we have identified a gap 
where unit tests do not fully cover how each component is tied together.
We should have integration tests to ensure everything ties together correctly
"""


# poetry run pytest -m integration
# run e2e against AWS - USE_MOCKS=false poetry run pytest -m e2e
@mock_aws
@pytest.mark.integration
@patch("dbt_platform_helper.utils.application.get_profile_name_from_account_id", return_value="foo")
@patch("dbt_platform_helper.utils.application.get_aws_session_or_abort", return_value=boto3)
def test_conduit(get_aws_session_or_abort, get_profile_name_from_account_id, setup_environment):
    CliRunner()

    with patch("subprocess.call") as mock_subprocess:
        mock_subprocess.return_value = 0
        result = CliRunner().invoke(
            conduit,
            # TODO should be parametised so when running e2e the test executes against a specific env
            [
                "fake-postgres",
                "--app",
                "test",
                "--env",
                "one",
                # --access read
            ],
        )

        print(result.output)
        assert result.exit_code == 0

        mock_subprocess.assert_has_calls(
            [call("copilot task run", shell=True), call("copilot task exec", shell=True)]
        )

        # TODO verify results in moto
        """
        mock_subprocess.call.assert_called_once_with(
            f"copilot task run --app test-application --env {env} "
            f"--task-group-name {task_name} "
            f"--image public.ecr.aws/uktrade/tunnel:{addon_type} "
            "--secrets CONNECTION_SECRET=test-arn "
            "--platform-os linux "
            "--platform-arch arm64",
            shell=True,
        )
        """


# TODO test already running task
