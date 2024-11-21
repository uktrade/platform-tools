import boto3
from moto import mock_aws

from dbt_platform_helper.providers.copilot import (
    get_postgres_connection_data_updated_with_master_secret,
)

env = "development"


@mock_aws
def test_update_postgres_parameter_with_master_secret():
    session = boto3.session.Session()

    parameter_name = "test-parameter"
    ssm_client = session.client("ssm")
    secretsmanager_client = session.client("secretsmanager")
    ssm_client.put_parameter(
        Name=parameter_name,
        Value='{"username": "read-only-user", "password": ">G12345", "host": "test.com", "port": 5432}',
        Type="String",
    )
    secret_arn = session.client("secretsmanager").create_secret(
        Name="master-secret", SecretString='{"username": "postgres", "password": ">G6789"}'
    )["ARN"]

    updated_parameter_value = get_postgres_connection_data_updated_with_master_secret(
        ssm_client, secretsmanager_client, parameter_name, secret_arn
    )

    assert updated_parameter_value == {
        "username": "postgres",
        "password": "%3EG6789",
        "host": "test.com",
        "port": 5432,
    }
