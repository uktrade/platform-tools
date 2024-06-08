import re
from pathlib import Path
from unittest.mock import patch

import boto3
import pytest
import yaml
from botocore.exceptions import ClientError
from moto import mock_aws
from schema import SchemaError

from dbt_platform_helper.utils.validation import AVAILABILITY_UNCERTAIN_TEMPLATE
from dbt_platform_helper.utils.validation import BUCKET_NAME_IN_USE_TEMPLATE
from dbt_platform_helper.utils.validation import S3_BUCKET_NAME_ERROR_TEMPLATE
from dbt_platform_helper.utils.validation import float_between_with_halfstep
from dbt_platform_helper.utils.validation import int_between
from dbt_platform_helper.utils.validation import validate_addons
from dbt_platform_helper.utils.validation import validate_s3_bucket_name
from dbt_platform_helper.utils.validation import validate_string
from dbt_platform_helper.utils.validation import warn_on_s3_bucket_name_availability
from tests.platform_helper.conftest import UTILS_FIXTURES_DIR
from tests.platform_helper.conftest import mock_aws_client


def load_addons(addons_file):
    with open(Path(UTILS_FIXTURES_DIR / "addons_files") / addons_file) as fh:
        return yaml.safe_load(fh)


@pytest.mark.parametrize(
    "regex_pattern, valid_string, invalid_string",
    [
        (r"^\d+-\d+$", "1-10", "20-21-23"),
        (r"^\d+s$", "10s", "10seconds"),
        (r"^((?!\*).)*(\*)?$", "test/valid/branch", "test*invalid/branch"),
        (r"^((?!\*).)*(\*)?$", "test/valid/branch*", "test*invalid/branch*"),
    ],
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
        "postgres_addons.yml",
        "redis_addons.yml",
        "opensearch_addons.yml",
        "monitoring_addons.yml",
        "no_param_addons.yml",
    ],
)
@patch("dbt_platform_helper.utils.validation.warn_on_s3_bucket_name_availability")
def test_validate_addons_success(mock_name_is_available, addons_file):
    mock_name_is_available.return_value = True
    errors = validate_addons(load_addons(addons_file))

    assert len(errors) == 0


@pytest.mark.parametrize(
    "addons_file, exp_error",
    [
        (
            "s3_addons_bad_data.yml",
            {
                "my-s3-bucket-readonly-should-be-bool": r"readonly.*should be instance of 'bool'",
                "my-s3-bucket-services-should-be-list": r"services.*should be instance of 'list'",
                "my-s3-bucket-service-should-be-string": r"services.*should be instance of 'str'",
                "my-s3-bucket-bad-name-suffix": r"Bucket name 'banana-s3alias' is invalid:\n  Names cannot be suffixed '-s3alias'",
                "my-s3-bucket-bad-deletion-policy": r"environments.*dev.*deletion_policy.*does not match False",
                "my-s3-bucket-objects-should-be-list": r"objects.*should be instance of 'list'",
                "my-s3-bucket-keys-should-be-string": r"objects.*key.*should be instance of 'str'",
                "my-s3-bucket-missing-key": r"objects.*Missing key: 'key'",
                "my-s3-bucket-body-should-be-string": r"objects.*body.*should be instance of 'str'",
                "my-s3-bucket-invalid-param": r"Wrong key 'unknown1'",
                "my-s3-bucket-invalid-object-param": r"objects.*Wrong key 'unknown2'",
                "my-s3-bucket-invalid-env-param": r"environments.*Wrong key 'unknown3'",
                "my-s3-bucket-retention-should-be-dict": r"retention_policy.*did not validate 'bad-policy'.*should be instance of 'dict'",
                "my-s3-bucket-invalid-retention-mode": r"mode.*GOVERNANCE.*does not match 'BAD_MODE'",
                "my-s3-bucket-invalid-param-combo": r"retention_policy.*There are multiple keys present from the .*'days'.*'years'.* condition",
                "my-s3-bucket-days-should-be-int": r"days.*should be instance of 'int'",
                "my-s3-bucket-years-should-be-int": r"years.*should be instance of 'int'",
                "my-s3-bucket-versioning-should-be-bool": r"environments.*versioning.*instance of 'bool'",
            },
        ),
        (
            "s3_policy_addons_bad_data.yml",
            {
                "my-s3-bucket-policy-readonly-should-be-bool": r"readonly.*should be instance of 'bool'",
                "my-s3-bucket-policy-services-should-be-list": r"services.*should be instance of 'list'",
                "my-s3-bucket-policy-service-should-be-string": r"services.*should be instance of 'str'",
                "my-s3-bucket-policy-bad-name-suffix": r"Bucket name 'banana-s3alias' is invalid:\n  Names cannot be suffixed '-s3alias'",
                "my-s3-bucket-policy-invalid-deletion-policy": r"environments.*dev.*deletion_policy.*does not match False",
                "my-s3-bucket-policy-invalid-param": r"Wrong key 'unknown1'",
                "my-s3-bucket-policy-invalid-object-param": r"Wrong key 'objects'",
                "my-s3-bucket-policy-invalid-env-param": r"environments.*Wrong key 'unknown3'",
            },
        ),
        (
            "aurora_addons_bad_data.yml",
            {
                "my-aurora-db-missing-version": r"Missing key: 'version'",
                "my-aurora-db-bad-deletion-policy": r"deletion_policy.*does not match 'None'",
                "my-aurora-db-bad-env-name": r"environments.*Missing key: Regex",
                "my-aurora-db-capacity-too-small": r"environments.*default.*min_capacity.*should be a number between 0.5 and 128 in increments of 0.5",
                "my-aurora-db-capacity-too-big": r"environments.*default.*max_capacity.*should be a number between 0.5 and 128 in increments of 0.5",
                "my-aurora-db-id-should-be-string": r"environments.*default.*snapshot_id.*should be instance of 'str'",
                "my-aurora-db-deletion-protection-should-be-bool": r"environments.*default.*deletion_protection.*should be instance of 'bool'",
                "my-aurora-db-invalid-deletion-policy": r"environments.*default.*deletion_policy.*does not match 'Slapstick'",
                "my-aurora-db-invalid-param": r"Wrong key 'bad_key'",
                "my-aurora-db-invalid-env-param": r"environments.*default.*Wrong key 'bad_env_key'",
            },
        ),
        (
            "postgres_addons_bad_data.yml",
            {
                "my-rds-db-invalid-param": r"Wrong key 'im_invalid' in",
                "my-rds-db-missing-version": r"Missing key: 'version'",
                "my-rds-db-bad-deletion-policy": r"did not validate 77",
                "my-rds-db-bad-plan": r"'environments'.*'default'.*'plan'.*does not match 'cunning'",
                "my-rds-db-volume-too-small": r"environments'.*'default'.*'volume_size'.*should be an integer between 20 and 10000",
                "my-rds-db-volume-too-big": r"environments'.*'default'.*'volume_size'.*should be an integer between 20 and 10000",
                "my-rds-db-volume-not-an-int": r"environments'.*'default'.*'volume_size'.*should be an integer between 20 and 10000",
                "my-rds-db-snapshot_id_should_be_a_str": r"'environments'.*'default'.*snapshot_id.*False should be instance of 'str'",
                "my-rds-db-invalid-policy": r"'environments'.*'default'.*deletion_policy.*'Snapshot' does not match 'None'",
                "my-rds-db-protection-should-be-bool": r"'environments'.*'default'.*deletion_protection.*12 should be instance of 'bool'",
                "my-rds-multi_az-should-be-bool": r"'environments'.*'default'.*multi_az.*10 should be instance of 'bool'",
                "my-rds-storage_type-should-valid-option": r"'environments'.*'default'.*storage_type.*'io2' does not match 'floppydisc'",
            },
        ),
        (
            "redis_addons_bad_data.yml",
            {
                "my-redis-bad-key": r"Wrong key 'bad_key' in",
                "my-redis-bad-engine-size": r"environments.*default.*engine.*'6.2' does not match 'a-big-engine'",
                "my-redis-bad-plan": r"environments.*default.*plan.*does not match 'enormous'",
                "my-redis-too-many-replicas": r"environments.*default.*replicas.*should be an integer between 0 and 5",
                "my-redis-bad-deletion-policy": r"environments.*default.*deletion_policy.*does not match 'Never'",
                "my-redis-apply-immediately-should-be-bool": r"'environments'.*'default'.*apply_immediately.*should be instance of 'bool'",
                "my-redis-automatic-failover-enabled-should-be-bool": r"'environments'.*'default'.*automatic_failover_enabled.*should be instance of 'bool'",
                "my-redis-instance-should-be-string": r"'environments'.*'default'.*instance.*should be instance of 'str'",
                "my-redis-multi-az-enabled-should-be-bool": r"'environments'.*'default'.*multi_az_enabled.*should be instance of 'bool'",
            },
        ),
        (
            "opensearch_addons_bad_data.yml",
            {
                "my-opensearch-bad-param": r"Wrong key 'nonsense' in",
                "my-opensearch-environments-should-be-list": r"environments.*False should be instance of 'dict'",
                "my-opensearch-bad-env-param": r"environments.*Wrong key 'opensearch_plan'",
                "my-opensearch-bad-plan": r"environments.*dev.*plan.*does not match 'largish'",
                "my-opensearch-bad-engine-size": r"environments.*dev.*engine.*does not match 7.3",
                "my-opensearch-no-plan": r"Missing key: 'plan'",
                "my-opensearch-volume-size-too-small": r"environments.*dev.*volume_size.*should be an integer greater than 10",
                "my-opensearch-invalid-size-for-small": r"environments.*dev.*volume_size.*should be an integer between 10 and [0-9]{2,4}.* for plan.*",
                "my-opensearch-invalid-size-for-large": r"environments.*production.*volume_size.*should be an integer between 10 and [0-9]{2,4}.* for plan.*",
                "my-opensearch-invalid-deletion-policy": r"environments.*dev.*deletion_policy.*does not match 'Snapshot'",
                "my-opensearch-instances-should-be-int": r"environments.*instances.*should be instance of 'int'",
                "my-opensearch-master-should-be-bool": r"environments.*master.*should be instance of 'bool'",
                "my-opensearch-es-app-log-retention-in-days-should-be-int": r"environments.*es_app_log_retention_in_days.*should be instance of 'int'",
                "my-opensearch-index-slow-log-retention-in-days-should-be-int": r"environments.*index_slow_log_retention_in_days.*should be instance of 'int'",
                "my-opensearch-audit-log-retention-in-days-should-be-int": r"environments.*audit_log_retention_in_days.*should be instance of 'int'",
                "my-opensearch-search-slow-log-retention-in-days-should-be-int": r"environments.*search_slow_log_retention_in_days.*should be instance of 'int'",
            },
        ),
        (
            "monitoring_addons_bad_data.yml",
            {
                "my-monitoring-bad-param": r"Wrong key 'monitoring_param' in",
                "my-monitoring-envs-should-be-list": r"environments.*'prod' should be instance of 'dict'",
                "my-monitoring-env-should-be-dict": r"environments.*default.*should be instance of 'dict'",
                "my-monitoring-enable-ops-center-should-be-bool": r"environments.*default.*enable_ops_center.* should be instance of 'bool'",
            },
        ),
        (
            "no_param_addons_bad_data.yml",
            {
                "my-appconfig-ipfilter": r"Wrong key 'appconfig_param' in",
                "my-subscription-filter": r"Wrong key 'sub_filter_param' in",
                "my-vpc": r"Wrong key 'vpc_param' in",
                "my-xray": r"Wrong key 'xray_param' in",
                "my-alb": r"Wrong key 'alb_param' in",
            },
        ),
    ],
)
@patch("dbt_platform_helper.utils.validation.warn_on_s3_bucket_name_availability")
def test_validate_addons_failure(mock_name_is_available, addons_file, exp_error):
    mock_name_is_available.return_value = True
    error_map = validate_addons(load_addons(addons_file))
    for entry, error in exp_error.items():
        assert entry in error_map
        assert bool(re.search(f"(?s)Error in {entry}:.*{error}", error_map[entry]))


@patch("dbt_platform_helper.utils.validation.warn_on_s3_bucket_name_availability")
def test_validate_addons_invalid_env_name_errors(mock_name_is_available):
    mock_name_is_available.return_value = True
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


@pytest.mark.parametrize("http_code", ["403", "400"])
@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
def test_validate_addons_unavailable_bucket_name(mock_get_session, http_code, capfd):
    client = mock_aws_client(mock_get_session)
    client.head_bucket.side_effect = ClientError({"Error": {"Code": http_code}}, "HeadBucket")
    validate_addons(
        {
            "my-s3": {
                "type": "s3",
                "environments": {"dev": {"bucket_name": "bucket"}},
            }
        }
    )

    assert BUCKET_NAME_IN_USE_TEMPLATE.format("bucket") in capfd.readouterr().out


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
@patch("dbt_platform_helper.utils.validation.warn_on_s3_bucket_name_availability")
def test_validate_s3_bucket_name_success_cases(mock_name_is_available, bucket_name):
    mock_name_is_available.return_value = True
    assert validate_s3_bucket_name(bucket_name)
    mock_name_is_available.assert_called_once()


@pytest.mark.parametrize("http_code", ["403", "400"])
@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
def test_validate_s3_bucket_name_failure_shows_warning(mock_get_session, http_code, capfd):
    client = mock_aws_client(mock_get_session)
    client.head_bucket.side_effect = ClientError({"Error": {"Code": http_code}}, "HeadBucket")
    bucket_name = "bucket-name"

    validate_s3_bucket_name(bucket_name)

    assert BUCKET_NAME_IN_USE_TEMPLATE.format(bucket_name) in capfd.readouterr().out


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
@patch("dbt_platform_helper.utils.validation.warn_on_s3_bucket_name_availability")
def test_validate_s3_bucket_name_failure_cases(mock_name_is_available, bucket_name, error_message):
    exp_error = S3_BUCKET_NAME_ERROR_TEMPLATE.format(bucket_name, f"  {error_message}")
    with pytest.raises(SchemaError) as ex:
        validate_s3_bucket_name(bucket_name)

    assert exp_error in str(ex.value)
    # We don't want to call out to AWS if the name isn't even valid.
    mock_name_is_available.assert_not_called()


@pytest.mark.parametrize("http_code", ["403", "400"])
@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
def test_warn_on_s3_bucket_name_availability_fails_40x(mock_get_session, http_code, capfd):
    client = mock_aws_client(mock_get_session)
    client.head_bucket.side_effect = ClientError({"Error": {"Code": http_code}}, "HeadBucket")

    warn_on_s3_bucket_name_availability(f"bucket-name-{http_code}")

    assert BUCKET_NAME_IN_USE_TEMPLATE.format(f"bucket-name-{http_code}") in capfd.readouterr().out


@mock_aws
def test_warn_on_s3_bucket_name_availability_success_200(capfd):
    client = boto3.client("s3")
    client.create_bucket(
        Bucket="bucket-name-200", CreateBucketConfiguration={"LocationConstraint": "eu-west-1"}
    )

    warn_on_s3_bucket_name_availability(f"bucket-name-200")
    assert "Warning:" not in capfd.readouterr().out


@mock_aws
def test_warn_on_s3_bucket_name_availability(clear_session_cache, capfd):
    warn_on_s3_bucket_name_availability("brand-new-bucket")
    assert "Warning:" not in capfd.readouterr().out


@pytest.mark.parametrize(
    "response",
    [
        {"Error": {"Code": "500"}},
        {},
    ],
)
@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
def test_warn_on_s3_bucket_name_availability_error_conditions_display_error(
    mock_get_session, response, capfd, clear_session_cache
):
    client = mock_aws_client(mock_get_session)
    client.head_bucket.side_effect = ClientError(response, "HeadBucket")

    warn_on_s3_bucket_name_availability("brand-new-bucket")

    assert AVAILABILITY_UNCERTAIN_TEMPLATE.format("brand-new-bucket") in capfd.readouterr().out


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
