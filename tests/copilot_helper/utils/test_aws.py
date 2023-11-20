from unittest.mock import patch

import boto3
import pytest
from moto import mock_ssm

from dbt_copilot_helper.exceptions import ValidationException
from dbt_copilot_helper.utils.aws import NoProfileForAccountIdError
from dbt_copilot_helper.utils.aws import get_aws_session_or_abort
from dbt_copilot_helper.utils.aws import get_codestar_connection_arn
from dbt_copilot_helper.utils.aws import get_profile_name_from_account_id
from dbt_copilot_helper.utils.aws import get_ssm_secrets
from dbt_copilot_helper.utils.aws import set_ssm_param
from tests.copilot_helper.conftest import mock_codestar_connections_boto_client


def test_get_aws_session_or_abort_profile_not_configured(capsys):
    with pytest.raises(SystemExit):
        get_aws_session_or_abort("foo")

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


@pytest.mark.parametrize(
    "overwrite, exists",
    [(False, False), (False, True)],
)
@mock_ssm
def test_set_ssm_param(overwrite, exists):
    mocked_ssm = boto3.client("ssm")

    set_ssm_param(
        "test-application",
        "development",
        "/copilot/test-application/development/secrets/TEST_SECRET",
        "random value",
        overwrite,
        exists,
        "Created for testing purposes.",
    )

    params = dict(
        Path="/copilot/test-application/development/secrets/",
        Recursive=False,
        WithDecryption=True,
        MaxResults=10,
    )

    result = mocked_ssm.get_parameters_by_path(**params)["Parameters"][0]

    expected_response = {
        "ARN": "arn:aws:ssm:eu-west-2:123456789012:parameter/copilot/test-application/development/secrets/TEST_SECRET",
        "Name": "/copilot/test-application/development/secrets/TEST_SECRET",
        "Type": "SecureString",
        "Value": "random value",
    }

    # assert result is a superset of expected_response
    assert result.items() >= expected_response.items()


@mock_ssm
def test_set_ssm_param_with_existing_secret():
    mocked_ssm = boto3.client("ssm")

    mocked_ssm.put_parameter(
        Name="/copilot/test-application/development/secrets/TEST_SECRET",
        Description="A test parameter",
        Value="test value",
        Type="SecureString",
    )

    params = dict(
        Path="/copilot/test-application/development/secrets/",
        Recursive=False,
        WithDecryption=True,
        MaxResults=10,
    )

    assert mocked_ssm.get_parameters_by_path(**params)["Parameters"][0]["Value"] == "test value"

    set_ssm_param(
        "test-application",
        "development",
        "/copilot/test-application/development/secrets/TEST_SECRET",
        "overwritten value",
        True,
        True,
        "Created for testing purposes.",
    )

    result = mocked_ssm.get_parameters_by_path(**params)["Parameters"][0]["Value"]

    assert result != "test value"
    assert result == "overwritten value"


@mock_ssm
def test_set_ssm_param_with_overwrite_but_not_exists():
    mocked_ssm = boto3.client("ssm")

    mocked_ssm.put_parameter(
        Name="/copilot/test-application/development/secrets/TEST_SECRET",
        Description="A test parameter",
        Value="test value",
        Type="SecureString",
    )

    params = dict(
        Path="/copilot/test-application/development/secrets/",
        Recursive=False,
        WithDecryption=True,
        MaxResults=10,
    )

    assert mocked_ssm.get_parameters_by_path(**params)["Parameters"][0]["Value"] == "test value"

    with pytest.raises(ValidationException) as exception:
        set_ssm_param(
            "test-application",
            "development",
            "/copilot/test-application/development/secrets/TEST_SECRET",
            "overwritten value",
            True,
            False,
            "Created for testing purposes.",
        )

    assert (
        """Arguments "overwrite" is set to True, but "exists" is set to False."""
        == exception.value.args[0]
    )


@mock_ssm
def test_set_ssm_param_tags():
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

    parameters = mocked_ssm.describe_parameters(
        ParameterFilters=[
            {"Key": "tag:copilot-application", "Values": ["test-application"]},
            {"Key": "tag:copilot-environment", "Values": ["development"]},
        ]
    )["Parameters"]

    assert len(parameters) == 1
    assert parameters[0]["Name"] == "/copilot/test-application/development/secrets/TEST_SECRET"

    response = mocked_ssm.describe_parameters(ParameterFilters=[{"Key": "tag:copilot-application"}])

    assert len(response["Parameters"]) == 1
    assert {parameter["Name"] for parameter in response["Parameters"]} == {
        "/copilot/test-application/development/secrets/TEST_SECRET"
    }


@mock_ssm
def test_set_ssm_param_tags_with_existing_secret():
    mocked_ssm = boto3.client("ssm")

    secret_name = "/copilot/test-application/development/secrets/TEST_SECRET"
    tags = [
        {"Key": "copilot-application", "Value": "test-application"},
        {"Key": "copilot-environment", "Value": "development"},
    ]

    mocked_ssm.put_parameter(
        Name=secret_name,
        Description="A test parameter",
        Value="test value",
        Type="SecureString",
        Tags=tags,
    )

    assert (
        tags
        == mocked_ssm.list_tags_for_resource(ResourceType="Parameter", ResourceId=secret_name)[
            "TagList"
        ]
    )

    set_ssm_param(
        "test-application",
        "development",
        secret_name,
        "random value",
        True,
        True,
        "Created for testing purposes.",
    )

    assert (
        tags
        == mocked_ssm.list_tags_for_resource(ResourceType="Parameter", ResourceId=secret_name)[
            "TagList"
        ]
    )


@patch("boto3.client")
@pytest.mark.parametrize(
    "connection_names, app_name, expected_arn",
    [
        [
            [
                "test-app-name",
            ],
            "test-app-name",
            f"arn:aws:codestar-connections:eu-west-2:1234567:connection/test-app-name",
        ],
        [
            [
                "test-app-name-1",
                "test-app-name-2",
                "test-app-name-3",
            ],
            "test-app-name-2",
            f"arn:aws:codestar-connections:eu-west-2:1234567:connection/test-app-name-2",
        ],
        [
            [
                "test-app-name",
            ],
            "test-app-name-2",
            None,
        ],
    ],
)
def test_get_codestar_connection_arn(mocked_boto3_client, connection_names, app_name, expected_arn):
    mock_codestar_connections_boto_client(mocked_boto3_client, connection_names)

    result = get_codestar_connection_arn(app_name)

    assert result == expected_arn


def test_get_profile_name_from_account_id(fakefs):
    assert get_profile_name_from_account_id("000000000") == "development"
    assert get_profile_name_from_account_id("111111111") == "staging"
    assert get_profile_name_from_account_id("222222222") == "production"


def test_get_profile_name_from_account_id_with_no_matching_account(fakefs):
    with pytest.raises(NoProfileForAccountIdError) as error:
        get_profile_name_from_account_id("999999999")

    assert str(error.value) == "No profile found for account 999999999"
