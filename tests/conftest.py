import os
import shutil
from pathlib import Path

import boto3
import jsonschema
import pytest
import yaml
from moto import mock_acm
from moto import mock_ecs
from moto import mock_iam
from moto import mock_route53
from moto import mock_secretsmanager

BASE_DIR = Path(__file__).parent.parent
TEST_APP_DIR = BASE_DIR / "tests" / "test-application"
FIXTURES_DIR = BASE_DIR / "tests" / "fixtures"


# tell yaml to ignore CFN ! function prefixes
yaml.add_multi_constructor("!", lambda loader, suffix, node: None, Loader=yaml.SafeLoader)


@pytest.fixture
def fakefs(fs):
    """Mock file system fixture with the templates and schemas dirs retained."""
    fs.add_real_directory(BASE_DIR / "commands/templates")
    fs.add_real_directory(BASE_DIR / "commands/schemas")
    fs.add_real_file(BASE_DIR / "commands/addon-plans.yml")
    fs.add_real_file(BASE_DIR / "commands/default-addons.yml")
    fs.add_real_file(BASE_DIR / "commands/addons-template-map.yml")
    fs.add_real_directory(Path(jsonschema.__path__[0]) / "schemas/vocabularies")

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
                {"key": "copilot-application", "value": "dbt-app"},
                {"key": "copilot-environment", "value": "staging"},
                {"key": "aws:cloudformation:logical-id", "value": "Cluster"},
            ]
        )


@pytest.fixture(scope="function")
def mocked_pg_secret():
    with mock_secretsmanager():
        yield boto3.client("secretsmanager").create_secret(
            Name="/copilot/dbt-app/staging/secrets/POSTGRES",
            SecretString='{"password":"abc123","dbname":"main","engine":"postgres","port":5432,"dbInstanceIdentifier":"dbt-app-staging-addons-postgresdbinstance-blah","host":"dbt-app-staging-addons-postgresdbinstance-blah.whatever.eu-west-2.rds.amazonaws.com","username":"postgres"}',
        )


def switch_to_tmp_dir_and_copy_config_file(tmp_path, valid_config_file, destination_filename):
    os.chdir(tmp_path)
    Path(destination_filename).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(f"{BASE_DIR}/tests/{valid_config_file}", destination_filename)
