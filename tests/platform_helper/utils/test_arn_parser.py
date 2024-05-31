import pytest
from parameterized import parameterized

from dbt_platform_helper.exceptions import ValidationException
from dbt_platform_helper.utils.arn_parser import ARN


def test_arn_parser_properties():
    source_arn = "arn:partition:service:region:account-id:resource-type:resource-id"
    arn = ARN(source_arn)

    assert arn.source == source_arn
    assert arn.partition == "partition"
    assert arn.service == "service"
    assert arn.region == "region"
    assert arn.account_id == "account-id"
    assert arn.project == "resource-type"
    assert arn.build_id == "resource-id"


@parameterized.expand(
    [
        "",
        "arn:partition:service:region:account-id",
    ]
)
def test_arn_parser_raises_error_if_arn_not_valid(arn):
    with pytest.raises(ValidationException, match=f"Invalid ARN: {arn}"):
        ARN(arn)
