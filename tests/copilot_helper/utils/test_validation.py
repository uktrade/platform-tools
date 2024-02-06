import re
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from botocore.exceptions import ClientError
from schema import SchemaError

from dbt_copilot_helper.utils.validation import AVAILABILITY_UNCERTAIN
from dbt_copilot_helper.utils.validation import S3_BUCKET_NAME_ERROR_TEMPLATE
from dbt_copilot_helper.utils.validation import float_between_with_halfstep
from dbt_copilot_helper.utils.validation import int_between
from dbt_copilot_helper.utils.validation import s3_bucket_name_is_available
from dbt_copilot_helper.utils.validation import validate_addons
from dbt_copilot_helper.utils.validation import validate_s3_bucket_name
from dbt_copilot_helper.utils.validation import validate_string
from tests.copilot_helper.conftest import UTILS_FIXTURES_DIR
from tests.copilot_helper.conftest import mock_aws_client


def load_addons(addons_file):
    with open(Path(UTILS_FIXTURES_DIR / "addons_files") / addons_file) as fh:
        return yaml.safe_load(fh)


@pytest.mark.parametrize(
    "regex_pattern, valid_string, invalid_string",
    [(r"^\d+-\d+$", "1-10", "20-21-23"), (r"^\d+s$", "10s", "10seconds")],
)
def test_validate_string(regex_pattern, valid_string, invalid_string):
    validator = validate_string(regex_pattern)

    assert validator(valid_string) == valid_string

    with pytest.raises(SchemaError) as err:
        validator(invalid_string)

    assert (
        err.value.args[0]
        == f"String '{invalid_string}' does not match the required pattern '{regex_pattern}'. For "
        "more details on valid string patterns see: "
        "https://aws.github.io/copilot-cli/docs/manifest/lb-web-service/"
    )


@pytest.mark.parametrize(
    "addons_file",
    [
        "s3_addons.yml",
        "s3_policy_addons.yml",
        "aurora_addons.yml",
        "rds_addons.yml",
        "redis_addons.yml",
        "opensearch_addons.yml",
        "monitoring_addons.yml",
        "no_param_addons.yml",
    ],
)
def test_validate_addons_success(addons_file):
    errors = validate_addons(load_addons(addons_file))

    assert len(errors) == 0


@pytest.mark.parametrize(
    "addons_file, exp_error",
    [
        (
            "s3_addons_bad_data.yml",
            {
                "my-s3-bucket-1": r"readonly.*should be instance of 'bool'",
                "my-s3-bucket-2": r"deletion_policy.*does not match 'Retrain'",
                "my-s3-bucket-3": r"services.*should be instance of 'list'",
                "my-s3-bucket-4": r"services.*should be instance of 'str'",
                "my-s3-bucket-5": r"Bucket name 'banana-s3alias' is invalid:\n  Names cannot be suffixed '-s3alias'",
                "my-s3-bucket-6": r"environments.*dev.*deletion_policy.*does not match False",
                "my-s3-bucket-7": r"objects.*should be instance of 'list'",
                "my-s3-bucket-8": r"objects.*key.*should be instance of 'str'",
                "my-s3-bucket-9": r"objects.*Missing key: 'key'",
                "my-s3-bucket-10": r"objects.*body.*should be instance of 'str'",
                "my-s3-bucket-11": r"Wrong key 'unknown1'",
                "my-s3-bucket-12": r"objects.*Wrong key 'unknown2'",
                "my-s3-bucket-13": r"environments.*Wrong key 'unknown3'",
            },
        ),
        (
            "s3_policy_addons_bad_data.yml",
            {
                "my-s3-bucket-policy-1": r"readonly.*should be instance of 'bool'",
                "my-s3-bucket-policy-2": r"deletion_policy.*does not match 'Retrain'",
                "my-s3-bucket-policy-3": r"services.*should be instance of 'list'",
                "my-s3-bucket-policy-4": r"services.*should be instance of 'str'",
                "my-s3-bucket-policy-5": r"Bucket name 'banana-s3alias' is invalid:\n  Names cannot be suffixed '-s3alias'",
                "my-s3-bucket-policy-6": r"environments.*dev.*deletion_policy.*does not match False",
                "my-s3-bucket-policy-7": r"Wrong key 'unknown1'",
                "my-s3-bucket-policy-8": r"Wrong key 'objects'",
                "my-s3-bucket-policy-9": r"environments.*Wrong key 'unknown3'",
            },
        ),
        (
            "aurora_addons_bad_data.yml",
            {
                "my-aurora-db-1": r"Missing key: 'version'",
                "my-aurora-db-2": r"deletion_policy.*does not match 'None'",
                "my-aurora-db-3": r"environments.*Missing key: Regex",
                "my-aurora-db-4": r"environments.*default.*min_capacity.*should be a number between 0.5 and 128 in increments of 0.5",
                "my-aurora-db-5": r"environments.*default.*max_capacity.*should be a number between 0.5 and 128 in increments of 0.5",
                "my-aurora-db-6": r"environments.*default.*snapshot_id.*should be instance of 'str'",
                "my-aurora-db-7": r"environments.*default.*deletion_protection.*should be instance of 'bool'",
                "my-aurora-db-8": r"environments.*default.*deletion_policy.*does not match 'Slapstick'",
                "my-aurora-db-9": r"Wrong key 'bad_key'",
                "my-aurora-db-10": r"environments.*default.*Wrong key 'bad_env_key'",
            },
        ),
        (
            "rds_addons_bad_data.yml",
            {
                "my-rds-db-1": r"Wrong key 'im_invalid' in",
                "my-rds-db-2": r"Missing key: 'version'",
                "my-rds-db-3": r"did not validate 77",
                "my-rds-db-4": r"'environments'.*'default'.*'plan'.*does not match 'cunning'",
                "my-rds-db-5a": r"environments'.*'default'.*'volume_size'.*should be an integer between 5 and 10000",
                "my-rds-db-5b": r"environments'.*'default'.*'volume_size'.*should be an integer between 5 and 10000",
                "my-rds-db-5c": r"environments'.*'default'.*'volume_size'.*should be an integer between 5 and 10000",
                "my-rds-db-6": r"'environments'.*'default'.*snapshot_id.*False should be instance of 'str'",
                "my-rds-db-7": r"'environments'.*'default'.*deletion_policy.*'Snapshot' does not match 'None'",
                "my-rds-db-8": r"'environments'.*'default'.*deletion_protection.*12 should be instance of 'bool'",
            },
        ),
        (
            "redis_addons_bad_data.yml",
            {
                "my-redis-1": r"Wrong key 'bad_key' in",
                "my-redis-2": r"deletion_policy.*'Retain' does not match 'Disabled'",
                "my-redis-3": r"environments.*default.*engine.*'6.2' does not match 'a-big-engine'",
                "my-redis-4": r"environments.*default.*plan.*does not match 'enormous'",
                "my-redis-5": r"environments.*default.*replicas.*should be an integer between 0 and 5",
                "my-redis-6": r"environments.*default.*deletion_policy.*does not match 'Never'",
            },
        ),
        (
            "opensearch_addons_bad_data.yml",
            {
                "my-opensearch-1": r"Wrong key 'nonsense' in",
                "my-opensearch-2": r"deletion_policy.*does not match 27",
                "my-opensearch-3": r"environments.*False should be instance of 'dict'",
                "my-opensearch-4": r"environments.*Wrong key 'opensearch_plan'",
                "my-opensearch-5": r"environments.*dev.*plan.*does not match 'largish'",
                "my-opensearch-6": r"environments.*dev.*engine.*does not match 7.3",
                "my-opensearch-7a": r"Missing key: 'plan'",
                "my-opensearch-7b": r"environments.*dev.*volume_size.*should be an integer greater than 10",
                "my-opensearch-7c": r"environments.*dev.*volume_size.*should be an integer between 10 and [0-9]{2,4}.* for plan.*",
                "my-opensearch-7d": r"environments.*production.*volume_size.*should be an integer between 10 and [0-9]{2,4}.* for plan.*",
                "my-opensearch-8": r"environments.*dev.*deletion_policy.*does not match 'Snapshot'",
            },
        ),
        (
            "monitoring_addons_bad_data.yml",
            {
                "my-monitoring-1": r"Wrong key 'monitoring_param' in",
                "my-monitoring-2": r"environments.*'prod' should be instance of 'dict'",
                "my-monitoring-3": r"environments.*default.*should be instance of 'dict'",
                "my-monitoring-4": r"environments.*default.*enable_ops_center.* should be instance of 'bool'",
            },
        ),
        (
            "no_param_addons_bad_data.yml",
            {
                "my-appconfig-ipfilter": r"Wrong key 'appconfig_param' in",
                "my-subscription-filter": r"Wrong key 'sub_filter_param' in",
                "my-vpc": r"Wrong key 'vpc_param' in",
                "my-xray": r"Wrong key 'xray_param' in",
            },
        ),
    ],
)
def test_validate_addons_failure(addons_file, exp_error):
    error_map = validate_addons(load_addons(addons_file))
    for entry, error in exp_error.items():
        assert entry in error_map
        assert bool(re.search(f"(?s)Error in {entry}:.*{error}", error_map[entry]))


def test_validate_addons_invalid_env_name_errors():
    error_map = validate_addons(
        {
            "my-s3": {
                "type": "s3",
                "environments": {"dev": {"bucket_name": "bucket"}, "hyphens-not-allowed": {}},
            }
        }
    )
    assert bool(
        re.search(
            f"(?s)Error in my-s3:.*environments.*Wrong key 'hyphens-not-allowed'",
            error_map["my-s3"],
        )
    )


def test_validate_addons_unsupported_addon():
    error_map = validate_addons(load_addons("unsupported_addon.yml"))
    for entry, error in error_map.items():
        assert "Unsupported addon type 'unsupported_addon' in addon 'my-unsupported-addon'" == error


def test_validate_addons_missing_type():
    error_map = validate_addons(load_addons("missing_type_addon.yml"))
    assert (
        "Missing addon type in addon 'my-missing-type-addon'" == error_map["my-missing-type-addon"]
    )
    assert "Missing addon type in addon 'my-empty-type-addon'" == error_map["my-empty-type-addon"]


@pytest.mark.parametrize("value", [5, 1, 9])
def test_between_success(value):
    assert int_between(1, 9)(value)


@pytest.mark.parametrize("value", [-1, 10])
def test_between_raises_error(value):
    try:
        int_between(1, 9)(value)
        assert False, f"testing that {value} is between 1 and 9 failed to raise an error."
    except SchemaError as ex:
        assert ex.code == "should be an integer between 1 and 9"


@pytest.mark.parametrize("value", [50.5, 33, 0.5, 128, 128.0])
def test_between_with_step_success(value):
    assert float_between_with_halfstep(0.5, 128)(value)


@pytest.mark.parametrize("value", [-1, 128.5, 20.3, 67.9])
def test_between_with_step_raises_error(value):
    try:
        float_between_with_halfstep(0.5, 128)(value)
        assert (
            False
        ), f"testing that {value} is between 0.5 and 128 in half steps failed to raise an error."
    except SchemaError as ex:
        assert ex.code == "should be a number between 0.5 and 128 in increments of 0.5"


@pytest.mark.parametrize("bucket_name", ["abc", "a" * 63, "abc-123.xyz", "123", "257.2.2.2"])
def test_validate_s3_bucket_name_success_cases(bucket_name):
    assert validate_s3_bucket_name(bucket_name)


@pytest.mark.parametrize(
    "bucket_name, error_message",
    [
        ("ab", "Length must be between 3 and 63 characters inclusive."),
        ("a" * 64, "Length must be between 3 and 63 characters inclusive."),
        ("ab!cd", "Names can only contain the characters 0-9, a-z, '.' and '-'."),
        ("ab_cd", "Names can only contain the characters 0-9, a-z, '.' and '-'."),
        ("aB-cd", "Names can only contain the characters 0-9, a-z, '.' and '-'."),
        ("-aB-cd", "Names must start and end with 0-9 or a-z."),
        ("aB-cd.", "Names must start and end with 0-9 or a-z."),
        ("ab..cd", "Names cannot contain two adjacent periods."),
        ("1.1.1.1", "Names cannot be IP addresses."),
        ("127.0.0.1", "Names cannot be IP addresses."),
        ("xn--bob", "Names cannot be prefixed 'xn--'."),
        ("sthree-bob", "Names cannot be prefixed 'sthree-'."),
        ("bob-s3alias", "Names cannot be suffixed '-s3alias'."),
        ("bob--ol-s3", "Names cannot be suffixed '--ol-s3'."),
    ],
)
def test_validate_s3_bucket_name_failure_cases(bucket_name, error_message):
    exp_error = S3_BUCKET_NAME_ERROR_TEMPLATE.format(bucket_name, f"  {error_message}")
    with pytest.raises(SchemaError) as ex:
        validate_s3_bucket_name(bucket_name)

    assert exp_error in str(ex.value)


@patch("dbt_copilot_helper.utils.validation.get_aws_session_or_abort")
def test_s3_bucket_name_is_available_200(mock_get_session):
    client = mock_aws_client(mock_get_session)
    client.head_bucket.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

    assert not s3_bucket_name_is_available(f"bucket_name_200")


@pytest.mark.parametrize("http_code", ["403", "400"])
@patch("dbt_copilot_helper.utils.validation.get_aws_session_or_abort")
def test_s3_bucket_name_is_available_400(mock_get_session, http_code):
    client = mock_aws_client(mock_get_session)
    client.head_bucket.side_effect = ClientError({"Error": {"Code": http_code}}, "HeadBucket")

    assert not s3_bucket_name_is_available(f"bucket_name_{http_code}")


@patch("dbt_copilot_helper.utils.validation.get_aws_session_or_abort")
def test_s3_bucket_name_is_available(mock_get_session):
    client = mock_aws_client(mock_get_session)
    client.head_bucket.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadBucket")

    assert s3_bucket_name_is_available("brand-new-bucket")


@pytest.mark.parametrize(
    "response",
    [
        {"Error": {"Code": "500"}},
        {},
    ],
)
@patch("dbt_copilot_helper.utils.validation.get_aws_session_or_abort")
def test_s3_bucket_name_is_available_error_conditions_display_error(
    mock_get_session, response, capfd
):
    client = mock_aws_client(mock_get_session)
    client.head_bucket.side_effect = ClientError(response, "HeadBucket")

    is_available = s3_bucket_name_is_available("brand-new-bucket")

    assert is_available
    assert AVAILABILITY_UNCERTAIN.format("brand-new-bucket") in capfd.readouterr().out


def test_validate_s3_bucket_name_multiple_failures():
    bucket_name = "xn--one-two..THREE" + "z" * 50 + "--ol-s3"
    with pytest.raises(SchemaError) as ex:
        validate_s3_bucket_name(bucket_name)

    exp_errors = [
        "Length must be between 3 and 63 characters inclusive.",
        "Names can only contain the characters 0-9, a-z, '.' and '-'.",
        "Names cannot contain two adjacent periods.",
        "Names cannot be prefixed 'xn--'.",
        "Names cannot be suffixed '--ol-s3'.",
    ]
    for exp_error in exp_errors:
        assert exp_error in str(ex.value)
