import json

import boto3
import pytest
from moto import mock_aws

from dbt_platform_helper.providers.secrets import AddonNotFoundError
from dbt_platform_helper.providers.secrets import AddonTypeMissingFromConfigError
from dbt_platform_helper.providers.secrets import InvalidAddonTypeError
from dbt_platform_helper.providers.secrets import ParameterNotFoundError
from dbt_platform_helper.providers.secrets import SecretNotFoundError
from dbt_platform_helper.providers.secrets import Secrets
from tests.platform_helper.conftest import add_addon_config_parameter
from tests.platform_helper.conftest import mock_parameter_name

env = "development"


@pytest.mark.parametrize(
    "test_string",
    [
        ("app-rds-postgres", "APP_RDS_POSTGRES"),
        ("APP-POSTGRES", "APP_POSTGRES"),
        ("APP-OpenSearch", "APP_OPENSEARCH"),
    ],
)
def test_normalise_secret_name(test_string, mock_application):
    """Test that given an addon name, normalise_secret_name produces the
    expected result."""

    ssm_client = mock_application.environments[env].session.client("ssm")
    secrets_client = mock_application.environments[env].session.client("secretsmanager")
    secrets_manager = Secrets(ssm_client, secrets_client, mock_application.name, env)

    assert secrets_manager._normalise_secret_name(test_string[0]) == test_string[1]


@mock_aws
def test_get_connection_secret_arn_from_secrets_manager(mock_application):
    """Test that, given app, environment and secret name strings,
    get_connection_secret_arn returns an ARN from secrets manager."""

    secret_name = f"/copilot/{mock_application.name}/development/secrets/POSTGRES"
    mock_secretsmanager = boto3.client("secretsmanager")
    mock_secretsmanager.create_secret(
        Name=secret_name,
        SecretString="something-secret",
    )

    ssm_client = mock_application.environments[env].session.client("ssm")
    secrets_client = mock_application.environments[env].session.client("secretsmanager")

    secrets_manager = Secrets(ssm_client, secrets_client, mock_application.name, env)

    arn = secrets_manager.get_connection_secret_arn(secret_name)

    assert arn.startswith(
        "arn:aws:secretsmanager:eu-west-2:123456789012:secret:"
        "/copilot/test-application/development/secrets/POSTGRES-"
    )


@mock_aws
def test_get_connection_secret_arn_from_parameter_store(mock_application):
    """Test that, given app, environment and secret name strings,
    get_connection_secret_arn returns an ARN from parameter store."""

    secret_name = f"/copilot/{mock_application.name}/development/secrets/POSTGRES"
    ssm_client = mock_application.environments[env].session.client("ssm")
    secrets_client = mock_application.environments[env].session.client("secretsmanager")

    ssm_client.put_parameter(
        Name=secret_name,
        Value="something-secret",
        Type="SecureString",
    )

    secrets_manager = Secrets(ssm_client, secrets_client, mock_application.name, env)

    arn = secrets_manager.get_connection_secret_arn(secret_name)

    assert (
        arn
        == "arn:aws:ssm:eu-west-2:123456789012:parameter/copilot/test-application/development/secrets/POSTGRES"
    )


@mock_aws
def test_get_connection_secret_arn_when_secret_does_not_exist(mock_application):
    """Test that, given app, environment and secret name strings,
    get_connection_secret_arn raises an exception when no matching secret exists
    in secrets manager or parameter store."""

    ssm_client = mock_application.environments[env].session.client("ssm")
    secrets_client = mock_application.environments[env].session.client("secretsmanager")
    secrets_manager = Secrets(ssm_client, secrets_client, mock_application.name, env)

    with pytest.raises(SecretNotFoundError) as ex:
        secrets_manager.get_connection_secret_arn("POSTGRES")


@mock_aws
def test_update_postgres_parameter_with_master_secret(mock_application):
    session = boto3.session.Session()

    parameter_name = "test-parameter"
    ssm_client = session.client("ssm")
    session.client("secretsmanager")
    ssm_client.put_parameter(
        Name=parameter_name,
        Value='{"username": "read-only-user", "password": ">G12345", "host": "test.com", "port": 5432}',
        Type="String",
    )
    secret_arn = session.client("secretsmanager").create_secret(
        Name="master-secret", SecretString='{"username": "postgres", "password": ">G6789"}'
    )["ARN"]

    ssm_client = mock_application.environments[env].session.client("ssm")
    secrets_client = mock_application.environments[env].session.client("secretsmanager")
    secrets_manager = Secrets(ssm_client, secrets_client, mock_application.name, env)

    updated_parameter_value = (
        secrets_manager.get_postgres_connection_data_updated_with_master_secret(
            parameter_name, secret_arn
        )
    )

    assert updated_parameter_value == {
        "username": "postgres",
        "password": "%3EG6789",
        "host": "test.com",
        "port": 5432,
    }


@mock_aws
@pytest.mark.parametrize(
    "addon_name, expected_type",
    [
        ("custom-name-postgres", "postgres"),
        ("custom-name-redis", "redis"),
        ("custom-name-opensearch", "opensearch"),
    ],
)
def test_get_addon_type(addon_name, expected_type, mock_application):
    """Test that get_addon_type returns the expected addon type."""

    ssm_client = mock_application.environments[env].session.client("ssm")
    secrets_client = mock_application.environments[env].session.client("secretsmanager")
    secrets_manager = Secrets(ssm_client, secrets_client, mock_application.name, env)

    add_addon_config_parameter()
    addon_type = secrets_manager.get_addon_type(addon_name)

    assert addon_type == expected_type


@mock_aws
def test_get_addon_type_with_not_found_throws_exception(mock_application):
    """Test that get_addon_type raises the expected error when the addon is not
    found in the config file."""

    add_addon_config_parameter({"different-name": {"type": "redis"}})
    ssm_client = mock_application.environments[env].session.client("ssm")
    secrets_client = mock_application.environments[env].session.client("secretsmanager")
    secrets_manager = Secrets(ssm_client, secrets_client, mock_application.name, env)

    with pytest.raises(AddonNotFoundError):
        secrets_manager.get_addon_type("custom-name-postgres")


@mock_aws
def test_get_addon_type_with_parameter_not_found_throws_exception(mock_application):
    """Test that get_addon_type raises the expected error when the addon config
    parameter is not found."""

    ssm_client = mock_application.environments[env].session.client("ssm")
    secrets_client = mock_application.environments[env].session.client("secretsmanager")
    secrets_manager = Secrets(ssm_client, secrets_client, mock_application.name, env)

    mock_ssm = boto3.client("ssm")
    mock_ssm.put_parameter(
        Name=f"/copilot/applications/test-application/environments/development/invalid-parameter",
        Type="String",
        Value=json.dumps({"custom-name-postgres": {"type": "postgres"}}),
    )

    with pytest.raises(ParameterNotFoundError):
        secrets_manager.get_addon_type("custom-name-postgres")


@mock_aws
def test_get_addon_type_with_invalid_type_throws_exception(mock_application):
    """Test that get_addon_type raises the expected error when the config
    contains an invalid addon type."""

    add_addon_config_parameter(param_value={"invalid-extension": {"type": "invalid"}})
    ssm_client = mock_application.environments[env].session.client("ssm")
    secrets_client = mock_application.environments[env].session.client("secretsmanager")
    secrets_manager = Secrets(ssm_client, secrets_client, mock_application.name, env)

    with pytest.raises(InvalidAddonTypeError):
        secrets_manager.get_addon_type("invalid-extension")


@mock_aws
def test_get_addon_type_with_blank_type_throws_exception(mock_application):
    """Test that get_addon_type raises the expected error when the config
    contains an empty addon type."""

    add_addon_config_parameter(param_value={"blank-extension": {}})
    ssm_client = mock_application.environments[env].session.client("ssm")
    secrets_client = mock_application.environments[env].session.client("secretsmanager")
    secrets_manager = Secrets(ssm_client, secrets_client, mock_application.name, env)

    with pytest.raises(AddonTypeMissingFromConfigError):
        secrets_manager.get_addon_type("blank-extension")


@mock_aws
def test_get_addon_type_with_unspecified_type_throws_exception(mock_application):
    """Test that get_addon_type raises the expected error when the config
    contains an empty addon type."""

    add_addon_config_parameter(param_value={"addon-type-unspecified": {"type": None}})
    ssm_client = mock_application.environments[env].session.client("ssm")
    secrets_client = mock_application.environments[env].session.client("secretsmanager")
    secrets_manager = Secrets(ssm_client, secrets_client, mock_application.name, env)

    with pytest.raises(AddonTypeMissingFromConfigError):
        secrets_manager.get_addon_type("addon-type-unspecified")


@mock_aws
@pytest.mark.parametrize(
    "access",
    [
        "read",
        "write",
        "admin",
    ],
)
@pytest.mark.parametrize(
    "addon_type, addon_name",
    [
        ("postgres", "custom-name-postgres"),
        ("postgres", "custom-name-rds-postgres"),
        ("redis", "custom-name-redis"),
        ("opensearch", "custom-name-opensearch"),
        ("s3", "custon-name-s3"),
    ],
)
def test_get_parameter_name(access, addon_type, addon_name, mock_application):
    """Test that get_parameter_name builds the correct parameter name given the
    addon_name, addon_type and permission."""

    ssm_client = mock_application.environments[env].session.client("ssm")
    secrets_client = mock_application.environments[env].session.client("secretsmanager")
    secrets_manager = Secrets(ssm_client, secrets_client, mock_application.name, env)
    parameter_name = secrets_manager.get_parameter_name(addon_type, addon_name, access)
    assert parameter_name == mock_parameter_name(mock_application, addon_type, addon_name, access)
