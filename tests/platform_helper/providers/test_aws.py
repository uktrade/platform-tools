import boto3
import pytest
from moto import mock_aws

from dbt_platform_helper.providers.aws import SecretNotFoundError
from dbt_platform_helper.providers.aws import get_connection_secret_arn

env = "development"


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

    arn = get_connection_secret_arn(ssm_client, secrets_client, secret_name)

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

    arn = get_connection_secret_arn(ssm_client, secrets_client, secret_name)

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

    with pytest.raises(SecretNotFoundError):
        get_connection_secret_arn(ssm_client, secrets_client, "POSTGRES")
