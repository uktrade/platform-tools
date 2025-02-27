import boto3
from botocore.stub import Stubber

from dbt_platform_helper.providers.parameter_store import ParameterStore


def test_get_ssm_paramter_by_name_sucess():
    """Test that given a parameter name, get_ssm_parameter_by_name successfully
    retrieves the parameter from parameter store."""

    paramter_name = "connors-ssm-parameter"
    ssm_client = boto3.client("ssm")
    expected_response = {"Name": paramter_name, "Value": "some-super-cool-string"}

    stubbed_ssm_client = Stubber(ssm_client)
    stubbed_ssm_client.add_response(
        "get_parameters", {"Parameters": [expected_response]}, {"Names": [paramter_name]}
    )

    with stubbed_ssm_client:
        response = ParameterStore(ssm_client=ssm_client).get_ssm_parameter_value_by_name(
            paramter_name
        )

    assert response == expected_response
    stubbed_ssm_client.assert_no_pending_responses()
