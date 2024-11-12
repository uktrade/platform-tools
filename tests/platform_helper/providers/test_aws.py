from moto import mock_aws


@mock_aws
def test_get_connection_secret_arn_from_secrets_manager(mock_application):
    """Test that, given app, environment and secret name strings,
    get_connection_secret_arn returns an ARN from secrets manager."""
    from dbt_platform_helper.commands.conduit import get_connection_secret_arn

    secret_name = f"/copilot/{mock_application.name}/development/secrets/POSTGRES"
    mock_secretsmanager = boto3.client("secretsmanager")
    mock_secretsmanager.create_secret(
        Name=secret_name,
        SecretString="something-secret",
    )

    arn = get_connection_secret_arn(mock_application, "development", secret_name)

    assert arn.startswith(
        "arn:aws:secretsmanager:eu-west-2:123456789012:secret:"
        "/copilot/test-application/development/secrets/POSTGRES-"
    )


@mock_aws
def test_get_connection_secret_arn_from_parameter_store(mock_application):
    """Test that, given app, environment and secret name strings,
    get_connection_secret_arn returns an ARN from parameter store."""
    from dbt_platform_helper.commands.conduit import get_connection_secret_arn

    secret_name = f"/copilot/{mock_application.name}/development/secrets/POSTGRES"
    mock_ssm = boto3.client("ssm")
    mock_ssm.put_parameter(
        Name=secret_name,
        Value="something-secret",
        Type="SecureString",
    )

    arn = get_connection_secret_arn(mock_application, "development", secret_name)

    assert (
        arn
        == "arn:aws:ssm:eu-west-2:123456789012:parameter/copilot/test-application/development/secrets/POSTGRES"
    )


@mock_aws
def test_get_connection_secret_arn_when_secret_does_not_exist(mock_application):
    """Test that, given app, environment and secret name strings,
    get_connection_secret_arn raises an exception when no matching secret exists
    in secrets manager or parameter store."""
    from dbt_platform_helper.commands.conduit import SecretNotFoundConduitError
    from dbt_platform_helper.commands.conduit import get_connection_secret_arn

    with pytest.raises(SecretNotFoundConduitError):
        get_connection_secret_arn(mock_application, "development", "POSTGRES")
