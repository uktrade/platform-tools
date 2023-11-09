import json
from pathlib import Path
from unittest.mock import patch

import boto3
import certifi
import jsonschema
import pytest
import yaml
from moto import mock_acm
from moto import mock_ec2
from moto import mock_ecs
from moto import mock_iam
from moto import mock_route53
from moto import mock_secretsmanager
from moto.ec2 import utils as ec2_utils

BASE_DIR = Path(__file__).parent.parent.parent
TEST_APP_DIR = BASE_DIR / "tests" / "copilot_helper" / "test-application-deploy"
FIXTURES_DIR = BASE_DIR / "tests" / "copilot_helper" / "fixtures"
EXPECTED_FILES_DIR = BASE_DIR / "tests" / "copilot_helper" / "expected_files"
UTILS_FIXTURES_DIR = BASE_DIR / "tests" / "copilot_helper" / "utils" / "fixtures"
DOCS_DIR = BASE_DIR / "tests" / "copilot_helper" / "test-docs"

# tell yaml to ignore CFN ! function prefixes
yaml.add_multi_constructor("!", lambda loader, suffix, node: None, Loader=yaml.SafeLoader)


@pytest.fixture
def fakefs(fs):
    """Mock file system fixture with the templates and schemas dirs retained."""
    fs.add_real_directory(BASE_DIR / "dbt_copilot_helper/custom_resources")
    fs.add_real_directory(BASE_DIR / "dbt_copilot_helper/templates")
    fs.add_real_directory(BASE_DIR / "dbt_copilot_helper/schemas")
    fs.add_real_file(BASE_DIR / "dbt_copilot_helper/addon-plans.yml")
    fs.add_real_file(BASE_DIR / "dbt_copilot_helper/default-addons.yml")
    fs.add_real_file(BASE_DIR / "dbt_copilot_helper/addons-template-map.yml")
    fs.add_real_directory(Path(jsonschema.__path__[0]) / "schemas/vocabularies")

    # To avoid 'Could not find a suitable TLS CA certificate bundle...' error
    fs.add_real_file(Path(certifi.__file__).parent / "cacert.pem")

    return fs


@pytest.fixture(scope="function")
def aws_credentials(monkeypatch):
    """Mocked AWS Credentials for moto."""
    moto_credentials_file_path = Path(__file__).parent.absolute() / "dummy_aws_credentials"
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(moto_credentials_file_path))


@pytest.fixture(scope="function")
def acm_session(aws_credentials):
    with mock_acm():
        session = boto3.session.Session(profile_name="foo", region_name="eu-west-2")
        yield session.client("acm")


@pytest.fixture(scope="function")
def route53_session(aws_credentials):
    with mock_route53():
        session = boto3.session.Session(profile_name="foo", region_name="eu-west-2")
        yield session.client("route53")


@pytest.fixture
def alias_session(aws_credentials):
    with mock_iam():
        session = boto3.session.Session(region_name="eu-west-2")
        session.client("iam").create_account_alias(AccountAlias="foo")

        yield session


@pytest.fixture(scope="function")
def mocked_cluster():
    with mock_ecs():
        yield boto3.client("ecs").create_cluster(
            tags=[
                {"key": "copilot-application", "value": "test-application"},
                {"key": "copilot-environment", "value": "development"},
                {"key": "aws:cloudformation:logical-id", "value": "Cluster"},
            ]
        )


@pytest.fixture(scope="function")
def mock_cluster_client_task(mocked_cluster):
    def _setup(addon_type, agent_last_status="RUNNING", task_running=True):
        with mock_ec2():
            mocked_ecs_client = boto3.client("ecs")
            mocked_cluster_arn = mocked_cluster["cluster"]["clusterArn"]

            mocked_ec2_client = boto3.client("ec2")
            mocked_ec2_images = mocked_ec2_client.describe_images(Owners=["amazon"])["Images"]
            mocked_ec2_client.run_instances(
                ImageId=mocked_ec2_images[0]["ImageId"],
                MinCount=1,
                MaxCount=1,
            )
            mocked_ec2_instances = boto3.client("ec2").describe_instances()
            mocked_ec2_instance_id = mocked_ec2_instances["Reservations"][0]["Instances"][0][
                "InstanceId"
            ]

            mocked_ec2 = boto3.resource("ec2")
            mocked_ec2_instance = mocked_ec2.Instance(mocked_ec2_instance_id)
            mocked_instance_id_document = json.dumps(
                ec2_utils.generate_instance_identity_document(mocked_ec2_instance),
            )

            mocked_ecs_client.register_container_instance(
                cluster=mocked_cluster_arn,
                instanceIdentityDocument=mocked_instance_id_document,
            )
            mocked_task_definition_arn = mocked_ecs_client.register_task_definition(
                family=f"copilot-conduit-test-application-development-{addon_type}",
                containerDefinitions=[
                    {
                        "name": "test_container",
                        "image": "test_image",
                        "cpu": 256,
                        "memory": 512,
                        "essential": True,
                    }
                ],
            )["taskDefinition"]["taskDefinitionArn"]

            if task_running:
                mocked_ecs_client.run_task(
                    cluster=mocked_cluster_arn,
                    taskDefinition=mocked_task_definition_arn,
                    enableExecuteCommand=True,
                )

            def describe_tasks(cluster, tasks):
                """Moto does not yet provide the ability to mock an executable
                task and its managed agents / containers, so we need to patch
                the expected response."""
                if not task_running:
                    raise Exception

                return {
                    "tasks": [
                        {
                            "lastStatus": "RUNNING",
                            "containers": [
                                {
                                    "managedAgents": [
                                        {
                                            "name": "ExecuteCommandAgent",
                                            "lastStatus": agent_last_status,
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }

            mocked_ecs_client.describe_tasks = describe_tasks

            return mocked_ecs_client

    return _setup


@pytest.fixture(scope="function")
def mocked_pg_secret():
    with mock_secretsmanager():
        yield boto3.client("secretsmanager").create_secret(
            Name="/copilot/dbt-app/staging/secrets/POSTGRES",
            SecretString='{"password":"abc123","dbname":"main","engine":"postgres","port":5432,"dbInstanceIdentifier":"dbt-app-staging-addons-postgresdbinstance-blah","host":"dbt-app-staging-addons-postgresdbinstance-blah.whatever.eu-west-2.rds.amazonaws.com","username":"postgres"}',
        )


@pytest.fixture(scope="function")
def validate_version():
    with patch("dbt_copilot_helper.utils.versioning.get_app_versions") as get_app_versions:
        get_app_versions.return_value = ((1, 0, 0), (1, 0, 0))
        with patch(
            "dbt_copilot_helper.utils.versioning.validate_version_compatibility",
            side_effect=None,
            return_value=None,
        ) as patched:
            yield patched


@pytest.fixture(scope="function")
def mock_tool_versions():
    with patch("dbt_copilot_helper.utils.versioning.get_app_versions") as get_app_versions:
        with patch("dbt_copilot_helper.utils.versioning.get_aws_versions") as get_aws_versions:
            with patch(
                "dbt_copilot_helper.utils.versioning.get_copilot_versions"
            ) as get_copilot_versions:
                yield get_app_versions, get_aws_versions, get_copilot_versions


def mock_codestar_connection_response(app_name):
    return {
        "ConnectionName": app_name,
        "ConnectionArn": f"arn:aws:codestar-connections:eu-west-2:1234567:connection/{app_name}",
        "ProviderType": "GitHub",
        "OwnerAccountId": "not-interesting",
        "ConnectionStatus": "AVAILABLE",
        "HostArn": "not-interesting",
    }


def mock_codestar_connections_boto_client(mocked_boto3_client, connection_names):
    mocked_boto3_client.return_value = mocked_boto3_client
    mocked_boto3_client.list_connections.return_value = {
        "Connections": [mock_codestar_connection_response(name) for name in connection_names],
        "NextToken": "not-interesting",
    }


def assert_file_created_in_stdout(output_file, result):
    assert f"File {output_file.relative_to('.')} created" in result.stdout


def assert_file_overwritten_in_stdout(output_file, result):
    assert f"File {output_file.relative_to('.')} overwritten" in result.stdout
