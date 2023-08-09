import boto3
import pytest
from moto import mock_ssm

from commands.utils import check_aws_conn
from commands.utils import get_ssm_secrets
from commands.utils import set_ssm_param


def test_check_aws_conn_profile_not_configured(capsys):
    with pytest.raises(SystemExit):
        check_aws_conn("foo")

    captured = capsys.readouterr()

    assert """AWS profile "foo" is not configured.""" in captured.out


@mock_ssm
def test_get_ssm_secrets():
    mocked_ssm = boto3.client("ssm")
    mocked_ssm.put_parameter(
        Name="/copilot/test-application/development/secrets/TEST_SECRET",
        Description="A test parameter",
        Value="test value",
        Type="SecureString",
    )

    result = get_ssm_secrets("test-application", "development")

    assert result == [("/copilot/test-application/development/secrets/TEST_SECRET", "test value")]


@mock_ssm
def test_set_ssm_param(alias_session, aws_credentials):
    mocked_ssm = boto3.client("ssm")

    set_ssm_param(
        "test-application",
        "development",
        "/copilot/test-application/development/secrets/TEST_SECRET",
        "random value",
        False,
        False,
        "Created for testing purposes.",
    )

    params = dict(
        Path="/copilot/test-application/development/secrets/",
        Recursive=False,
        WithDecryption=True,
        MaxResults=10,
    )

    result = mocked_ssm.get_parameters_by_path(**params)["Parameters"][0]

    assert result["Name"] == "/copilot/test-application/development/secrets/TEST_SECRET"
