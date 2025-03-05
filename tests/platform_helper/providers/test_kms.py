import boto3
from botocore.stub import Stubber

from dbt_platform_helper.providers.kms import KMSProvider


def test_describe_key():
    """Test that given a kms alias, describe_key successfully retrieves related
    key metadata from KMS."""

    alias_name = "dummuy_key"
    kms_client = boto3.client("kms")
    expected_response = {
        "KeyMetadata": {
            "KeyId": "1-2-3-4-5",
        }
    }

    stubbed_kms_client = Stubber(kms_client)
    stubbed_kms_client.add_response("describe_key", expected_response, {"KeyId": alias_name})

    with stubbed_kms_client:
        response = KMSProvider(kms_client=kms_client).describe_key(alias_name=alias_name)

    assert response == expected_response
    stubbed_kms_client.assert_no_pending_responses()
