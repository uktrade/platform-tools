import boto3
import pytest
from botocore.stub import Stubber

from dbt_platform_helper.providers.parameter_store import (
    ParameterNotFoundForNameException,
)
from dbt_platform_helper.providers.parameter_store import ParameterStore


def test_get_ssm_parameter_by_name_sucess():
    """Test that given a parameter name, get_ssm_parameter_by_name successfully
    retrieves the parameter from parameter store."""

    parameter_name = "connors-ssm-parameter"
    ssm_client = boto3.client("ssm")
    expected_response = {"Name": parameter_name, "Value": "some-super-cool-string"}

    stubbed_ssm_client = Stubber(ssm_client)
    stubbed_ssm_client.add_response(
        "get_parameters", {"Parameters": [expected_response]}, {"Names": [parameter_name]}
    )

    with stubbed_ssm_client:
        response = ParameterStore(ssm_client=ssm_client).get_ssm_parameter_by_name(parameter_name)

    assert response == expected_response
    stubbed_ssm_client.assert_no_pending_responses()


def test_get_ssm_parameter_no_parameter_found():
    """Test that given a parameter name, get_ssm_parameter_by_name raises an
    error when no parameter is returned from AWS."""

    parameter_name = "connors-ssm-parameter-which-doesnt-exist"
    ssm_client = boto3.client("ssm")

    stubbed_ssm_client = Stubber(ssm_client)
    stubbed_ssm_client.add_response(
        "get_parameters", {"Parameters": []}, {"Names": [parameter_name]}
    )

    with stubbed_ssm_client:
        with pytest.raises(ParameterNotFoundForNameException):
            ParameterStore(ssm_client=ssm_client).get_ssm_parameter_by_name(parameter_name)

    stubbed_ssm_client.assert_no_pending_responses()
