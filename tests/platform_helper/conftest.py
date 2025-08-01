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
from botocore.exceptions import ClientError
from moto import mock_aws
from moto.ec2 import utils as ec2_utils

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.constants import PLATFORM_CONFIG_SCHEMA_VERSION
from dbt_platform_helper.constants import SERVICE_CONFIG_FILE
from dbt_platform_helper.constants import SERVICE_CONFIG_SCHEMA_VERSION
from dbt_platform_helper.constants import SERVICE_DIRECTORY
from dbt_platform_helper.providers.cache import Cache
from dbt_platform_helper.utils.aws import AWS_SESSION_CACHE

BASE_DIR = Path(__file__).parent.parent.parent
TEST_APP_DIR = BASE_DIR / "tests" / "platform_helper" / "test-application-deploy"
FIXTURES_DIR = BASE_DIR / "tests" / "platform_helper" / "fixtures"
INPUT_DATA_DIR = FIXTURES_DIR / "input_data"
EXPECTED_DATA_DIR = FIXTURES_DIR / "expected_data"
EXPECTED_FILES_DIR = BASE_DIR / "tests" / "platform_helper" / "expected_files"
UTILS_FIXTURES_DIR = BASE_DIR / "tests" / "platform_helper" / "utils" / "fixtures"
DOCS_DIR = BASE_DIR / "tests" / "platform_helper" / "test-docs"

# tell yaml to ignore CFN ! function prefixes
yaml.add_multi_constructor("!", lambda loader, suffix, node: None, Loader=yaml.SafeLoader)


class NoSuchEntityException(ClientError):
    """This is needed to simulate the NoSuchEntityException that is dynamically
    created by the boto3 error factory and so unavailable for import."""

    def __init__(self):
        self.response = {"Error": {"Code": "NoSuchEntity"}}


@pytest.fixture
def fakefs(fs):
    """Mock file system fixture with the templates and schemas dirs retained."""
    fs.add_real_directory(BASE_DIR / "dbt_platform_helper/templates", lazy_read=True)
    fs.add_real_directory(FIXTURES_DIR, lazy_read=True)
    fs.add_real_directory(EXPECTED_FILES_DIR, lazy_read=True)
    fs.add_real_file(BASE_DIR / "dbt_platform_helper/default-extensions.yml")
    fs.add_real_directory(BASE_DIR / "terraform", read_only=False, lazy_read=True)

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


@pytest.fixture()
def no_skipping_version_checks():
    with patch("dbt_platform_helper.domain.versioning.skip_version_checks") as skip_version_checks:
        skip_version_checks.return_value = False
        yield skip_version_checks


@pytest.fixture(scope="function", autouse=True)
def mock_application():
    with patch(
        "dbt_platform_helper.utils.application.load_application",
    ) as load_application:
        os.environ.pop("AWS_PROFILE", None)

        from dbt_platform_helper.utils.application import Application
        from dbt_platform_helper.utils.application import Environment
        from dbt_platform_helper.utils.application import Service

        sessions = {
            "000000000": boto3,
            "111111111": boto3,
            "222222222": boto3,
        }
        application = Application("test-application")
        application.environments["development"] = Environment("development", "000000000", sessions)
        application.environments["staging"] = Environment("staging", "111111111", sessions)
        application.environments["production"] = Environment("production", "222222222", sessions)
        application.services["web"] = Service("web", "Load Balanced Web Service")

        load_application.return_value = application

        yield application


@pytest.fixture(scope="function")
def aws_credentials(monkeypatch):
    """Mocked AWS Credentials for moto."""
    moto_credentials_file_path = Path(__file__).parent.absolute() / "dummy_aws_credentials"
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(moto_credentials_file_path))


@pytest.fixture(scope="function")
def acm_session(aws_credentials):
    with mock_aws():
        session = boto3.session.Session(profile_name="foo", region_name="eu-west-2")
        yield session.client("acm")


@pytest.fixture(scope="function")
def route53_session(aws_credentials):
    with mock_aws():
        session = boto3.session.Session(profile_name="foo", region_name="eu-west-2")
        yield session.client("route53")


@pytest.fixture
def alias_session(aws_credentials):
    with mock_aws():
        session = boto3.session.Session(region_name="eu-west-2")
        session.client("iam").create_account_alias(AccountAlias="foo")

        yield session


@pytest.fixture(scope="function")
def mocked_cluster():
    with mock_aws():
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
        with mock_aws():
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
def mock_stack():
    def _create_stack(addon_name):
        params = [
            {
                "ParameterKey": "ExistingParameter",
                "ParameterValue": "does-not-matter",
            }
        ]
        with mock_aws():
            with open(FIXTURES_DIR / "test_cloudformation_template.yml") as f:
                template = yaml.safe_load(f)
            cf = boto3.client("cloudformation")
            cf.create_stack(
                StackName=f"task-{mock_task_name(addon_name)}",
                TemplateBody=yaml.dump(template),
                Parameters=params,
            )

    return _create_stack


def mock_task_name(addon_name):
    return f"conduit-test-application-development-{addon_name}-tq7vzeigl2vf"


def mock_parameter_name(app, addon_type, addon_name, access: str = "read"):
    addon_name = addon_name.replace("-", "_").upper()
    if addon_type == "postgres":
        return f"/copilot/{app.name}/development/conduits/{addon_name}_{access.upper()}"
    elif addon_type == "redis" or addon_type == "opensearch":
        return f"/copilot/{app.name}/development/conduits/{addon_name}_ENDPOINT"
    else:
        return f"/copilot/{app.name}/development/conduits/{addon_name}"


def expected_connection_secret_name(mock_application, addon_type, addon_name, access):
    secret_name = f"/copilot/{mock_application.name}/development/secrets/{addon_name.replace('-', '_').upper()}"
    if addon_type == "postgres":
        if access == "read":
            return f"{secret_name}_READ_ONLY_USER"
        elif access == "write":
            return f"{secret_name}_APPLICATION_USER"
    elif addon_type == "redis" or addon_type == "opensearch":
        secret_name += "_ENDPOINT"

    return secret_name


def add_addon_config_parameter(param_value=None):
    mock_ssm = boto3.client("ssm")
    mock_ssm.put_parameter(
        Name=f"/copilot/applications/test-application/environments/development/addons",
        Type="String",
        Value=json.dumps(
            param_value
            or {
                "custom-name-postgres": {"type": "postgres"},
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


def mock_caller_id_boto_client(get_aws_session_or_abort, connection_names):
    client = mock_aws_client(get_aws_session_or_abort)

    client.get_caller_identity.return_value = {"Account": "000000000000"}


def mock_ecr_public_repositories_boto_client(get_aws_session_or_abort):
    client = mock_aws_client(get_aws_session_or_abort)

    client.describe_repositories.return_value = {
        "repositories": [
            {
                "repositoryArn": "arn:aws:ecr-public::000000000000:repository/my/app",
                "registryId": "000000000000",
                "repositoryName": "my/app",
                "repositoryUri": "public.ecr.aws/abc123/my/app",
            },
            {
                "repositoryArn": "arn:aws:ecr-public::000000000000:repository/my/app2",
                "registryId": "000000000000",
                "repositoryName": "my/app2",
                "repositoryUri": "public.ecr.aws/abc123/my/app2",
            },
        ]
    }


def mock_get_caller_identity(get_aws_session_or_abort):
    client = mock_aws_client(get_aws_session_or_abort)
    client.get_caller_identity.return_value = {"Account": "000000000000", "UserId": "abc123"}


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


@pytest.fixture()
def valid_platform_config():
    return yaml.safe_load(
        f"""
schema_version: {PLATFORM_CONFIG_SCHEMA_VERSION}
default_versions: 
  platform-helper: 14.0.0
application: test-app
default_versions: 
    platform-helper: 10.2.0
environments:
  "*":
    service-deployment-mode: copilot
    accounts:
      deploy:
        name: "non-prod-acc"
        id: "1122334455"
      dns:
        name: "non-prod-dns-acc"
        id: "6677889900"
    requires_approval: false
    vpc: non-prod-vpc
  dev: 
    service-deployment-mode: dual-deploy-copilot-traffic
  development:
    service-deployment-mode: dual-deploy-copilot-traffic
  test:
    service-deployment-mode: dual-deploy-platform-traffic
  staging:
    service-deployment-mode: platform
  hotfix:
    accounts:
      deploy:
        name: "prod-acc"
        id: "9999999999"
      dns:
        name: "non-prod-dns-acc"
        id: "6677889900"
    vpc: hotfix-vpc
  prod:
    accounts:
      deploy:
        name: "prod-acc"
        id: "9999999999"
      dns:
        name: "prod-dns-acc"
        id: "7777777777"
    requires_approval: true
    vpc: prod-vpc
  production:
    accounts:
      deploy:
        name: "prod-acc"
        id: "9999999999"
      dns:
        name: "prod-dns-acc"
        id: "7777777777"
    requires_approval: true
    vpc: prod-vpc

extensions:
  # If you wish to deploy a subset of the backing services for testing, make sure any you don't need are commented out
  test-app-redis:
    type: redis
    environments:
      "*":
        engine: '7.1'
        plan: tiny
        apply_immediately: true

  test-app-postgres:
    type: postgres
    version: 16.2
    environments:
      prod:
        backup_retention_days: 10
      hotfix:
        backup_retention_days: 10
      dev:
        deletion_protection: true
      staging:
        deletion_protection: true
        deletion_policy: Retain
    database_copy:
        - from: prod
          to: hotfix

  test-app-opensearch:
    type: opensearch
    environments:
      "*":
        plan: small
        engine: '1.3'
        volume_size: 40
        password_special_characters: "-_.,"
        urlencode_password: false

  test-app-s3-bucket-with-objects:
    type: s3
    services:
      - web
    environments:
      dev:
        bucket_name: test-app-dev
        versioning: false
        lifecycle_rules:
          - expiration_days: 1
            enabled: true
      staging:
        bucket_name: test-app-staging
        versioning: false
    objects:
      - key: healthcheck.txt
        body: Demodjango is working.

  test-app-s3-bucket:
    type: s3-policy
    services:
      - web
    environments:
      dev:
        bucket_name: test-app-policy-dev
  
  test-app-s3-bucket-data-migration:
    type: s3
    services: 
      - web
    environments:
      dev:
        bucket_name: s3-data-migration
        versioning: false
        data_migration:
          import: 
            source_bucket_arn: arn:aws:s3:::test-app
            source_kms_key_arn: arn:aws:kms::123456789012:key/test-key
            worker_role_arn: arn:aws:iam::123456789012:role/test-role 
        
  test-app-monitoring:
    type: monitoring
    environments:
      "*":
        enable_ops_center: false

  test-app-alb:
    type: alb
    environments:
      dev:
        cdn_domains_list:
          dev.test-app.uktrade.digital: "test-app.uktrade.digital"

environment_pipelines:
  main:
    account: non-prod-acc
    slack_channel: "/codebuild/notification_channel"
    trigger_on_push: true
    pipeline_to_trigger: "prod-main"
    environments:
      dev:
      staging:
  test:
    branch: my-feature-branch
    slack_channel: "/codebuild/notification_channel"
    trigger_on_push: false
    versions:
        platform-helper: main
    environments:
      test:
        requires_approval: true
        vpc: testing_vpc
        accounts:
          deploy:
            name: "prod-acc"
            id: "9999999999"
          dns:
            name: "prod-dns-acc"
            id: "7777777777"
  prod-main:
    account: prod-acc
    branch: main
    slack_channel: "/codebuild/slack_oauth_channel"
    trigger_on_push: false
    versions:
        platform-helper: 9.0.9
    environments:
      prod:
        requires_approval: true

codebase_pipelines:
  application:
    slack_channel: OTHER_SLACK_CHANNEL_ID
    repository: uktrade/test-app
    deploy_repository_branch: feature-branch
    additional_ecr_repository: public.ecr.aws/my-public-repo/test-app/application
    services:
        - run_order_1:
          - celery-worker
          - celery-beat
          - web
    pipelines:
      - name: main
        branch: main
        environments:
          - name: dev
      - name: tagged
        tag: true
        environments:
          - name: staging
            requires_approval: true
"""
    )


@pytest.fixture()
def valid_service_config():
    return yaml.safe_load(
        f"""
schema_version: {SERVICE_CONFIG_SCHEMA_VERSION}

name: web
type: Load Balanced Web Service

# Distribute traffic to your service.
http:
  # Requests to this path will be forwarded to your service.
  alias: web.${"{ENVIRONMENT_NAME}"}.test-app.uktrade.digital
  # To match all requests you can use the "/" path.
  path: '/'
  # You can specify a custom health check path. The default is "/".
  # healthcheck: '/'
  target_container: nginx
  healthcheck:
    path: '/'
    port: 8080
    success_codes: '200'
    healthy_threshold: 3
    unhealthy_threshold: 3
    interval: 35s
    timeout: 30s
    grace_period: 30s

sidecars:
  sidecar:
    port: 443
    image: public.ecr.aws//sidecar:tlatest
    variables:
      SERVER: localhost:8000


# Configuration for your containers and service.
image:
  location: public.ecr.aws/non-prod-acc/test-app/application:${"{IMAGE_TAG}"}
  # Port exposed through your container to route traffic to it.
  port: 8080

cpu: 512 # Number of CPU units for the task.
memory: 2048 # Amount of memory in MiB used by the task.
count: 1 # Number of tasks that should be running in your service.
exec: true # Enable running commands in your container.
network:
  connect: true # Enable Service Connect for intra-environment traffic between services.
  vpc:
    placement: 'private'

storage:
  readonly_fs: false

variables:  
  SECRET_KEY: testing-secret-key
  PORT: 8080
  DEBUG: False

secrets:
  DJANGO_SECRET_KEY: DJANGO_SECRET_KEY

environments:
  dev:
    http:
      alb: arn:aws:elasticloadbalancing:eu-west-2:1122334455:loadbalancer/app/test-app-dev/4c84af3e661d6ba0
  hotfix:
    http:
      alb: arn:aws:elasticloadbalancing:eu-west-2:9999999999:loadbalancer/app/test-app-hotfix/937d6308baba5404
  prod:
    http:
      alb: arn:aws:elasticloadbalancing:eu-west-2:9999999999:loadbalancer/app/test-app-prod/9df7e0985fc9a089
      alias: web.test-app.prod.uktrade.digital
    sidecars:
      datadog-agent:
        variables:
          DD_APM_ENABLED: true
  staging:
    variables:
      S3_CROSS_ENVIRONMENT_BUCKET_NAMES: test-app-hotfix-additional
    http:
      alb: arn:aws:elasticloadbalancing:eu-west-2:1122334455:loadbalancer/app/test-app-toolspr/e7d5af472c55e4d2
    sidecars:
      ipfilter:
        image: public.ecr.aws/uktrade/ip-filter:tag-latest
  test:
    http:
      alb: arn:aws:elasticloadbalancing:eu-west-2:1122334455:loadbalancer/app/test-app-hotfix/937d6308baba5404
"""
    )


@pytest.fixture
def platform_env_config():
    return {
        "schema_version": PLATFORM_CONFIG_SCHEMA_VERSION,
        "default_versions": {"platform-helper": "14.0.0"},
        "application": "my-app",
        "environments": {
            "*": {
                "accounts": {
                    "deploy": {"name": "non-prod-acc", "id": "1122334455"},
                    "dns": {"name": "non-prod-dns-acc", "id": "6677889900"},
                },
                "requires_approval": False,
                "vpc": "non-prod-vpc",
            },
            "dev": {},
            "staging": {},
            "prod": {
                "accounts": {
                    "deploy": {"name": "prod-acc", "id": "9999999999"},
                    "dns": {"name": "prod-dns-acc", "id": "7777777777"},
                },
                "requires_approval": True,
                "vpc": "prod-vpc",
            },
        },
    }


@pytest.fixture
def codebase_pipeline_config_for_1_pipeline_and_2_run_groups(platform_env_config):
    return {
        **platform_env_config,
        "default_versions": {"platform-helper": "14.0.0"},
        "codebase_pipelines": {
            "test_codebase": {
                "repository": "uktrade/repo1",
                "services": [
                    {"run_group_1": ["web"]},
                    {"run_group_2": ["api", "celery-worker"]},
                ],
                "pipelines": [
                    {"name": "main", "branch": "main", "environments": [{"name": "dev"}]},
                    {
                        "name": "tagged",
                        "tag": True,
                        "environments": [
                            {"name": "staging"},
                            {"name": "prod", "requires_approval": True},
                        ],
                    },
                ],
            }
        },
    }


@pytest.fixture
def codebase_pipeline_config_for_2_pipelines_and_1_run_group(
    codebase_pipeline_config_for_1_pipeline_and_2_run_groups,
):
    codebase_pipeline_config_for_1_pipeline_and_2_run_groups["codebase_pipelines"][
        "test_codebase_2"
    ] = {
        "repository": "uktrade/repo2",
        "services": [
            {"run_group_1": ["web"]},
        ],
        "pipelines": [
            {"name": "main", "branch": "main", "environments": [{"name": "dev"}]},
            {
                "name": "tagged",
                "tag": True,
                "environments": [
                    {"name": "staging"},
                ],
            },
        ],
    }
    return codebase_pipeline_config_for_1_pipeline_and_2_run_groups


@pytest.fixture
def s3_extensions_fixture(fakefs):
    fakefs.create_file(
        PLATFORM_CONFIG_FILE,
        contents=yaml.dump(
            {
                "application": "my_app",
                "extensions": {
                    "one": {
                        "type": "s3",
                        "environments": {
                            "env1": {"bucket_name": "bucket-one"},
                            "env2": {"bucket_name": "bucket-two"},
                        },
                    },
                    "two": {
                        "type": "s3-policy",
                        "environments": {
                            "env3": {"bucket_name": "bucket-three"},
                        },
                    },
                    "three": {
                        "type": "s3",
                    },
                },
            }
        ),
    )


INVALID_PLATFORM_CONFIG_WITH_PLATFORM_VERSION_OVERRIDES = """
application: invalid-config-app
legacy_project: false

default_versions: 
    platform-helper: 1.2.3

environments:
  dev:
  test:
  staging:
  prod:
    vpc: prod-vpc

extensions:
  test-app-s3-bucket:
    type: s3
    this_field_is_incompatible_with_current_version: foo
  
environment_pipelines:
  prod-main:
    account: prod-acc
    branch: main
    slack_channel: "/codebuild/slack_oauth_channel"
    trigger_on_push: false
    versions:
        platform-helper: 9.0.9
    environments:
      prod:
        requires_approval: true
"""


@pytest.fixture()
def platform_config_for_env_pipelines():
    return yaml.safe_load(
        f"""
schema_version: {PLATFORM_CONFIG_SCHEMA_VERSION}
default_versions: 
  platform-helper: 14.0.0
application: test-app
deploy_repository: uktrade/test-app-weird-name-deploy

environments:
  dev:
    accounts:
      deploy:
        name: "platform-sandbox-test"
        id: "1111111111"
      dns:
        name: "platform-sandbox-test"
        id: "2222222222"
  prod:
    accounts:
      deploy:
        name: "platform-prod-test"
        id: "3333333333"
      dns:
        name: "platform-prod-test"
        id: "4444444444"
    requires_approval: true

environment_pipelines:
   main:
       account: platform-sandbox-test
       branch: main
       slack_channel: "/codebuild/test-slack-channel"
       trigger_on_push: false
       environments:
         dev:
   prod-main:
       account: platform-prod-test
       branch: main
       slack_channel: "/codebuild/test-slack-channel"
       trigger_on_push: false
       environments:
         prod:
    """
    )


@pytest.fixture
def create_valid_platform_config_file(fakefs, valid_platform_config):
    fakefs.create_file(Path(PLATFORM_CONFIG_FILE), contents=yaml.dump(valid_platform_config))


@pytest.fixture
def create_invalid_platform_config_file(fakefs):
    fakefs.create_file(
        Path(PLATFORM_CONFIG_FILE),
        contents=INVALID_PLATFORM_CONFIG_WITH_PLATFORM_VERSION_OVERRIDES,
    )


@pytest.fixture
def create_service_directory(fakefs):
    fakefs.create_file(Path(f"{SERVICE_DIRECTORY}/fake-service/fake.example"))


@pytest.fixture
def create_valid_service_config_file(fakefs, valid_service_config):
    fakefs.create_file(
        Path(f"{SERVICE_DIRECTORY}/web/{SERVICE_CONFIG_FILE}"),
        contents=yaml.dump(valid_service_config),
    )


# TODO: DBTP-1969: - stop gap until validation.py is refactored into a class, then it will be an easier job of just passing in a mock_redis_provider into the constructor for the config_provider. For now autouse is needed.
@pytest.fixture(autouse=True)
def mock_get_data(request, monkeypatch):
    if "skip_mock_get_data" in request.keywords:
        return

    def mock_return_value(self, strategy):
        return ["6.2", "7.0", "7.1"]

    monkeypatch.setattr(Cache, "get_data", mock_return_value)
