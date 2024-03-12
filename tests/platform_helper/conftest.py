import json
import os
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import boto3
import botocore
import certifi
import pytest
import yaml
from moto import mock_acm
from moto import mock_cloudformation
from moto import mock_ec2
from moto import mock_ecs
from moto import mock_iam
from moto import mock_route53
from moto import mock_secretsmanager
from moto.ec2 import utils as ec2_utils

from dbt_platform_helper.utils.aws import AWS_SESSION_CACHE

BASE_DIR = Path(__file__).parent.parent.parent
TEST_APP_DIR = BASE_DIR / "tests" / "platform_helper" / "test-application-deploy"
FIXTURES_DIR = BASE_DIR / "tests" / "platform_helper" / "fixtures"
EXPECTED_FILES_DIR = BASE_DIR / "tests" / "platform_helper" / "expected_files"
UTILS_FIXTURES_DIR = BASE_DIR / "tests" / "platform_helper" / "utils" / "fixtures"
DOCS_DIR = BASE_DIR / "tests" / "platform_helper" / "test-docs"

# tell yaml to ignore CFN ! function prefixes
yaml.add_multi_constructor("!", lambda loader, suffix, node: None, Loader=yaml.SafeLoader)


@pytest.fixture
def fakefs(fs):
    """Mock file system fixture with the templates and schemas dirs retained."""
    fs.add_real_directory(BASE_DIR / "dbt_platform_helper/custom_resources", lazy_read=True)
    fs.add_real_directory(BASE_DIR / "dbt_platform_helper/templates", lazy_read=True)
    fs.add_real_directory(FIXTURES_DIR, lazy_read=True)
    fs.add_real_file(BASE_DIR / "dbt_platform_helper/addon-plans.yml")
    fs.add_real_file(BASE_DIR / "dbt_platform_helper/default-addons.yml")
    fs.add_real_file(BASE_DIR / "dbt_platform_helper/addons-template-map.yml")

    # To avoid 'Could not find a suitable TLS CA certificate bundle...' error
    fs.add_real_file(Path(certifi.__file__).parent / "cacert.pem")

    # For fakefs compatibility with moto
    fs.add_real_directory(Path(boto3.__file__).parent.joinpath("data"), lazy_read=True)
    fs.add_real_directory(Path(botocore.__file__).parent.joinpath("data"), lazy_read=True)

    # Add fake aws config file
    fs.add_real_file(
        FIXTURES_DIR / "dummy_aws_config.ini", True, Path.home().joinpath(".aws/config")
    )

    return fs


@pytest.fixture(scope="function")
def create_test_manifest(fakefs):
    fakefs.create_file(
        "copilot/manifest.yml",
        contents="""
environments:
  dev:
    http:
      alias: v2.app.dev.uktrade.digital

  staging:
    http:
      alias: v2.app.staging.uktrade.digital

  prod1:
    http:
      alias: v2.app.prod.uktrade.digital

  prod2:
    http:
      alias: v2.app.great.gov.uk

  prod3:
    http:
      alias: app.trade.gov.uk
""",
    )


@pytest.fixture(scope="function", autouse=True)
def mock_application():
    with patch(
        "dbt_platform_helper.utils.application.load_application",
    ) as load_application:
        os.environ.pop("AWS_PROFILE", None)

        from dbt_platform_helper.utils.application import Application
        from dbt_platform_helper.utils.application import Environment

        sessions = {
            "000000000": boto3,
            "111111111": boto3,
            "222222222": boto3,
        }
        application = Application("test-application")
        application.environments["development"] = Environment("development", "000000000", sessions)
        application.environments["staging"] = Environment("staging", "111111111", sessions)
        application.environments["production"] = Environment("production", "222222222", sessions)

        load_application.return_value = application

        yield application


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
                family=f"copilot-{mock_task_name(addon_type)}",
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
    with patch("dbt_platform_helper.utils.versioning.get_app_versions") as get_app_versions:
        get_app_versions.return_value = ((1, 0, 0), (1, 0, 0))
        with patch(
            "dbt_platform_helper.utils.versioning.validate_version_compatibility",
            side_effect=None,
            return_value=None,
        ) as patched:
            yield patched


@pytest.fixture(scope="function")
def mock_tool_versions():
    with patch("dbt_platform_helper.utils.versioning.get_app_versions") as get_app_versions:
        with patch("dbt_platform_helper.utils.versioning.get_aws_versions") as get_aws_versions:
            with patch(
                "dbt_platform_helper.utils.versioning.get_copilot_versions"
            ) as get_copilot_versions:
                yield get_app_versions, get_aws_versions, get_copilot_versions


@pytest.fixture(scope="function")
def mock_stack():
    def _create_stack(addon_name):
        with mock_cloudformation():
            with open(FIXTURES_DIR / "test_cloudformation_template.yml") as f:
                template = yaml.safe_load(f)
            cf = boto3.client("cloudformation")
            cf.create_stack(
                StackName=f"task-{mock_task_name(addon_name)}",
                TemplateBody=yaml.dump(template),
            )

    return _create_stack


def mock_task_name(addon_name):
    return f"conduit-test-application-development-{addon_name}-tq7vzeigl2vf"


def mock_parameter_name(app, addon_type, addon_name, access: str = "read"):
    addon_name = addon_name.replace("-", "_").upper()
    if addon_type == "postgres":
        return f"/copilot/{app.name}/development/conduits/{addon_name}_{access.upper()}"
    else:
        return f"/copilot/{app.name}/development/conduits/{addon_name}"


def mock_connection_secret_name(mock_application, addon_type, addon_name, access):
    secret_name = f"/copilot/{mock_application.name}/development/secrets/{addon_name.replace('-', '_').upper()}"
    if addon_type == "postgres":
        if access == "read":
            return f"{secret_name}_READ_ONLY_USER"
        elif access == "write":
            return f"{secret_name}_APPLICATION_USER"

    return secret_name


def add_addon_config_parameter(param_value=None):
    mock_ssm = boto3.client("ssm")
    mock_ssm.put_parameter(
        Name=f"/copilot/applications/test-application/environments/development/addons",
        Type="String",
        Value=json.dumps(
            param_value
            or {
                "custom-name-postgres": {"type": "aurora-postgres"},
                "custom-name-rds-postgres": {"type": "aurora-postgres"},
                "custom-name-opensearch": {"type": "opensearch"},
                "custom-name-redis": {"type": "redis"},
            }
        ),
    )


def mock_codestar_connection_response(app_name):
    return {
        "ConnectionName": app_name,
        "ConnectionArn": f"arn:aws:codestar-connections:eu-west-2:1234567:connection/{app_name}",
        "ProviderType": "GitHub",
        "OwnerAccountId": "not-interesting",
        "ConnectionStatus": "AVAILABLE",
        "HostArn": "not-interesting",
    }


def mock_codestar_connections_boto_client(get_aws_session_or_abort, connection_names):
    client = mock_aws_client(get_aws_session_or_abort)

    client.list_connections.return_value = {
        "Connections": [mock_codestar_connection_response(name) for name in connection_names],
        "NextToken": "not-interesting",
    }


def mock_aws_client(get_aws_session_or_abort, client=None):
    session = MagicMock(name="session-mock")
    session.profile_name = "foo"
    if not client:
        client = MagicMock(name="client-mock")
    session.client.return_value = client
    get_aws_session_or_abort.return_value = session

    return client


def assert_file_created_in_stdout(output_file, result):
    assert f"File {output_file.relative_to('.')} created" in result.stdout


def assert_file_overwritten_in_stdout(output_file, result):
    assert f"File {output_file.relative_to('.')} overwritten" in result.stdout


@pytest.fixture()
def clear_session_cache():
    AWS_SESSION_CACHE.clear()
