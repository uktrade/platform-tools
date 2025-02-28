import boto3
import pytest
from botocore.stub import Stubber

from dbt_platform_helper.providers.parameter_store import (
    ParameterNotFoundForNameException,
)
from dbt_platform_helper.providers.parameter_store import (
    ParameterNotFoundForPathException,
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


def test_get_ssm_parameters_by_path_success():
    """Test that given a parameter path, get_ssm_parameters_by_path successfully
    lists those parameters and returns them."""

    parameter_path = "/connors-ssm-parameters/connors-application/"
    ssm_client = boto3.client("ssm")
    expected_response = [
        {"Name": f"{parameter_path}parameter1", "Value": "some-super-cool-string"},
        {"Name": f"{parameter_path}parameter1", "Value": "some-super-cool-string"},
    ]

    stubbed_ssm_client = Stubber(ssm_client)
    stubbed_ssm_client.add_response(
        "get_parameters_by_path",
        {"Parameters": expected_response},
        {"Path": parameter_path, "Recursive": True},
    )

    with stubbed_ssm_client:
        result = ParameterStore(ssm_client=ssm_client).get_ssm_parameters_by_path(parameter_path)

    assert result == expected_response
    stubbed_ssm_client.assert_no_pending_responses()


def test_get_ssm_parameters_by_path_no_parameters_found():
    """Test that when the boto3 call get_parameters_by_path returns no
    parameters, the code successfully captures that and raises a
    ParametersNotFoundforPathException."""

    parameter_path = "/connors-ssm-parameters/bad-parameter-path/"
    ssm_client = boto3.client("ssm")

    stubbed_ssm_client = Stubber(ssm_client)
    stubbed_ssm_client.add_response(
        "get_parameters_by_path", {"Parameters": []}, {"Path": parameter_path, "Recursive": True}
    )

    with stubbed_ssm_client:
        with pytest.raises(ParameterNotFoundForPathException):
            ParameterStore(ssm_client=ssm_client).get_ssm_parameters_by_path(parameter_path)

    stubbed_ssm_client.assert_no_pending_responses()
