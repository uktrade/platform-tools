import re
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import boto3
import pytest
import yaml
from botocore.exceptions import ClientError
from moto import mock_aws
from schema import SchemaError

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_FILE
from dbt_platform_helper.utils.validation import AVAILABILITY_UNCERTAIN_TEMPLATE
from dbt_platform_helper.utils.validation import BUCKET_NAME_IN_USE_TEMPLATE
from dbt_platform_helper.utils.validation import S3_BUCKET_NAME_ERROR_TEMPLATE
from dbt_platform_helper.utils.validation import config_file_check
from dbt_platform_helper.utils.validation import float_between_with_halfstep
from dbt_platform_helper.utils.validation import int_between
from dbt_platform_helper.utils.validation import lint_yaml_for_duplicate_keys
from dbt_platform_helper.utils.validation import load_and_validate_platform_config
from dbt_platform_helper.utils.validation import validate_addons
from dbt_platform_helper.utils.validation import validate_database_copy_section
from dbt_platform_helper.utils.validation import validate_platform_config
from dbt_platform_helper.utils.validation import validate_s3_bucket_name
from dbt_platform_helper.utils.validation import validate_string
from dbt_platform_helper.utils.validation import warn_on_s3_bucket_name_availability
from tests.platform_helper.conftest import FIXTURES_DIR
from tests.platform_helper.conftest import UTILS_FIXTURES_DIR
from tests.platform_helper.conftest import mock_aws_client


def load_addons(addons_file):
    with open(Path(UTILS_FIXTURES_DIR / "addons_files") / addons_file) as fh:
        return yaml.safe_load(fh)


@pytest.mark.parametrize(
    "regex_pattern, valid_strings, invalid_strings",
    [
        (r"^\d+-\d+$", ["1-10"], ["20-21-23"]),
        (r"^\d+s$", ["10s"], ["10seconds"]),
        (
            r"^((?!\*).)*(\*)?$",
            ["test/valid/branch", "test/valid/branch*", "test/valid/branch-other"],
            ["test*invalid/branch", "test*invalid/branch*"],
        ),
    ],
)
def test_validate_string(regex_pattern, valid_strings, invalid_strings):
    validator = validate_string(regex_pattern)

    for valid_string in valid_strings:
        assert validator(valid_string) == valid_string

    for invalid_string in invalid_strings:
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
        "alb_addons.yml",
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
                "my-s3-bucket-lifecycle-enabled-should-be-bool": r"environments.*lifecycle_rules.*enabled.*instance of 'bool'",
                "my-s3-bucket-data-migration-source-bucket-invalid-arn": r"source_bucket_arn must contain a valid ARN for an S3 bucket",
                "my-s3-bucket-data-migration-source-kms-key-invalid-arn": r"source_kms_key_arn must contain a valid ARN for a KMS key",
                "my-s3-bucket-data-migration-worker-role-invalid-arn": r"worker_role_arn must contain a valid ARN for an IAM role",
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
                "my-rds-backup-retention-too-high": r"environments'.*'default'.*'backup_retention_days'.*should be an integer between 1 and 35",
                "my-rds-data-migration-invalid-environments": r"Environment name \$ is invalid: names must only contain lowercase alphanumeric characters, or be the '\*' default environment",
                "my-rds-data-migration-missing-key": r"Missing key: 'to'.*",
                "my-rds-data-migration-invalid-key": r"Wrong key 'non-existent-key' in.*",
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
                "my-opensearch-password-special-characters": r"environments.*password_special_characters.*should be instance of 'str'",
                "my-opensearch-urlencode-password": r"environments.*urlencode_password.*should be instance of 'bool'",
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
        (
            "prometheus_policy_addons_bad_data.yml",
            {
                "my-prometheus-policy-wrong-key": r"Missing key: 'role_arn'",
                "my-prometheus-policy-wrong-type": r"Key 'role_arn' error.*should be instance of 'str'",
            },
        ),
        (
            "alb_addons_bad_data.yml",
            {
                "my-alb-additional-address-list-should-be-a-list": r"environments.*dev.*should be instance of 'list'",
                "my-alb-allowed-methods-should-be-a-list": r"environments.*dev.*should be instance of 'list'",
                "my-alb-cached-methods-should-be-a-list": r"environments.*dev.*should be instance of 'list'",
                "my-alb-cdn-compress-should-be-a-bool": r"environments.*dev.*should be instance of 'bool'",
                "my-alb-cdn-domain-list-be-a-dict": r"environments.*dev.*should be instance of 'dict'",
                "my-cdn-geo-locations-be-a-list": r"environments.*dev.*should be instance of 'list'",
                "my-alb-cdn-geo-restrictions-type-should-be-a-string": r"environments.*dev.*should be instance of 'str'",
                "my-alb-cdn-logging-bucket-should-be-a-string": r"environments.*dev.*should be instance of 'str'",
                "my-alb-cdn-logging-bucket-prefix-should-be-a-string": r"environments.*dev.*should be instance of 'str'",
                "my-alb-default-waf-should-be-a-string": r"environments.*dev.*should be instance of 'str'",
                "my-alb-enable-logging-should-be-a-bool": r"environments.*dev.*should be instance of 'bool'",
                "my-alb-forwarded-values-forward-should-be-a-string": r"environments.*dev.*should be instance of 'str'",
                "my-alb-forwarded-values-headers-should-be-a-list": r"environments.*dev.*should be instance of 'list'",
                "my-alb-forwarded-values-query-string-should-be-a-bool": r"environments.*dev.*should be instance of 'bool'",
                "my-alb-origin-protocol-policy-should-be-a-string": r"environments.*dev.*should be instance of 'str'",
                "my-alb-origin-ssl-protocols-should-be-a-list": r"environments.*dev.*should be instance of 'list'",
                "my-alb-viewer-certificate-minimum-protocol-version-should-be-a-string": r"environments.*dev.*should be instance of 'str'",
                "my-alb-viewer-certificate-ssl-support-method-should-be-a-string": r"environments.*dev.*should be instance of 'str'",
                "my-alb-view-protocol-policy-should-be-a-string": r"environments.*dev.*should be instance of 'str'",
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
        Bucket="bucket-name-200", CreateBucketConfiguration={"LocationConstraint": "eu-west-2"}
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


@patch("dbt_platform_helper.utils.validation.warn_on_s3_bucket_name_availability")
def test_validate_platform_config_success(
    mock_warn_on_s3_bucket_name_availability, valid_platform_config
):
    validate_platform_config(valid_platform_config)
    assert mock_warn_on_s3_bucket_name_availability.called


@patch("dbt_platform_helper.utils.validation.warn_on_s3_bucket_name_availability")
def test_validate_platform_config_success_when_aws_validation_disabled(
    mock_warn_on_s3_bucket_name_availability, valid_platform_config
):
    validate_platform_config(valid_platform_config, disable_aws_validation=True)
    assert not mock_warn_on_s3_bucket_name_availability.called


@pytest.mark.parametrize("pipeline_to_trigger", ("", "non-existent-pipeline"))
@patch("dbt_platform_helper.utils.validation.warn_on_s3_bucket_name_availability", new=Mock())
@patch("dbt_platform_helper.utils.validation.abort_with_error")
def test_validate_platform_config_fails_if_pipeline_to_trigger_not_valid(
    mock_abort_with_error, valid_platform_config, pipeline_to_trigger
):
    valid_platform_config["environment_pipelines"]["main"][
        "pipeline_to_trigger"
    ] = pipeline_to_trigger

    validate_platform_config(valid_platform_config)
    message = mock_abort_with_error.call_args.args[0]

    assert "The following pipelines are misconfigured:" in message
    assert (
        f"  'main' - '{pipeline_to_trigger}' is not a valid target pipeline to trigger" in message
    )


@patch("dbt_platform_helper.utils.validation.warn_on_s3_bucket_name_availability", new=Mock())
@patch("dbt_platform_helper.utils.validation.abort_with_error")
def test_validate_platform_config_fails_with_multiple_errors_if_pipeline_to_trigger_is_invalid(
    mock_abort_with_error, valid_platform_config
):
    valid_platform_config["environment_pipelines"]["main"]["pipeline_to_trigger"] = ""
    valid_platform_config["environment_pipelines"]["test"][
        "pipeline_to_trigger"
    ] = "non-existent-pipeline"

    validate_platform_config(valid_platform_config)
    message = mock_abort_with_error.call_args.args[0]

    assert "The following pipelines are misconfigured:" in message
    assert f"  'main' - '' is not a valid target pipeline to trigger" in message
    assert (
        f"  'test' - 'non-existent-pipeline' is not a valid target pipeline to trigger" in message
    )


@patch("dbt_platform_helper.utils.validation.warn_on_s3_bucket_name_availability", new=Mock())
@patch("dbt_platform_helper.utils.validation.abort_with_error")
def test_validate_platform_config_fails_if_pipeline_to_trigger_is_triggering_itself(
    mock_abort_with_error, valid_platform_config
):
    valid_platform_config["environment_pipelines"]["main"]["pipeline_to_trigger"] = "main"

    validate_platform_config(valid_platform_config)
    message = mock_abort_with_error.call_args.args[0]

    assert "The following pipelines are misconfigured:" in message
    assert f"  'main' - pipelines cannot trigger themselves" in message


@pytest.mark.parametrize(
    "account, envs, exp_bad_envs",
    [
        ("account-does-not-exist", ["dev"], ["dev"]),
        ("prod-acc", ["dev", "staging", "prod"], ["dev", "staging"]),
        ("non-prod-acc", ["dev", "prod"], ["prod"]),
    ],
)
@patch("dbt_platform_helper.utils.validation.warn_on_s3_bucket_name_availability", new=Mock())
@patch("dbt_platform_helper.utils.validation.abort_with_error")
def test_validate_platform_config_fails_if_pipeline_account_does_not_match_environment_accounts_with_single_pipeline(
    mock_abort_with_error, platform_env_config, account, envs, exp_bad_envs
):
    platform_env_config["environment_pipelines"] = {
        "main": {
            "account": account,
            "slack_channel": "/codebuild/notification_channel",
            "trigger_on_push": True,
            "environments": {env: {} for env in envs},
        }
    }

    validate_platform_config(platform_env_config)

    message = mock_abort_with_error.call_args.args[0]

    assert "The following pipelines are misconfigured:" in message
    assert (
        f"  'main' - these environments are not in the '{account}' account: {', '.join(exp_bad_envs)}"
        in message
    )


@patch("dbt_platform_helper.utils.validation.warn_on_s3_bucket_name_availability", new=Mock())
@patch("dbt_platform_helper.utils.validation.abort_with_error")
def test_validate_platform_config_fails_if_database_copy_config_is_invalid(
    mock_abort_with_error,
):
    """Edge cases for this are all covered in unit tests of
    validate_database_copy_section elsewhere in this file."""
    config = {
        "application": "test-app",
        "environments": {"dev": {}, "test": {}, "prod": {}},
        "extensions": {
            "our-postgres": {
                "type": "postgres",
                "version": 7,
                "database_copy": [{"from": "dev", "to": "dev"}],
            }
        },
    }

    validate_platform_config(config)

    message = mock_abort_with_error.call_args.args[0]

    assert (
        f"database_copy 'to' and 'from' cannot be the same environment in extension 'our-postgres'."
        in message
    )


@patch("dbt_platform_helper.utils.validation.warn_on_s3_bucket_name_availability", new=Mock())
@patch("dbt_platform_helper.utils.validation.abort_with_error")
def test_validate_platform_config_catches_database_copy_errors(
    mock_abort_with_error, platform_env_config
):
    platform_env_config["environment_pipelines"] = {
        "main": {
            "account": "non-prod",
            "slack_channel": "/codebuild/notification_channel",
            "trigger_on_push": True,
            "environments": {"dev": {}, "prod": {}},
        },
        "prod": {
            "account": "prod",
            "slack_channel": "/codebuild/notification_channel",
            "trigger_on_push": True,
            "environments": {"dev": {}, "staging": {}, "prod": {}},
        },
    }

    validate_platform_config(platform_env_config)

    message = mock_abort_with_error.call_args.args[0]

    assert "The following pipelines are misconfigured:" in message
    assert f"  'main' - these environments are not in the 'non-prod' account: dev" in message
    assert f"  'prod' - these environments are not in the 'prod' account: dev, staging" in message


@pytest.mark.parametrize(
    "account, envs",
    [
        ("non-prod-acc", ["dev", "staging"]),
        ("prod-acc", ["prod"]),
    ],
)
@patch("dbt_platform_helper.utils.validation.warn_on_s3_bucket_name_availability", new=Mock())
def test_validate_platform_config_succeeds_if_pipeline_account_matches_environment_accounts(
    platform_env_config, account, envs
):
    platform_env_config["environment_pipelines"] = {
        "main": {
            "account": account,
            "slack_channel": "/codebuild/notification_channel",
            "trigger_on_push": True,
            "environments": {env: {} for env in envs},
        }
    }

    # Should not error if config is sound.
    validate_platform_config(platform_env_config)


@pytest.mark.parametrize(
    "yaml_file",
    [
        "pipeline/platform-config.yml",
        "pipeline/platform-config-with-public-repo.yml",
        "pipeline/platform-config-for-terraform.yml",
    ],
)
def test_load_and_validate_config_valid_file(yaml_file):
    """Test that, given the path to a valid yaml file, load_and_validate_config
    returns the loaded yaml unmodified."""

    path = FIXTURES_DIR / yaml_file
    validated = load_and_validate_platform_config(path=path)

    with open(path, "r") as fd:
        conf = yaml.safe_load(fd)

    assert validated == conf


def test_lint_yaml_for_duplicate_keys_fails_when_duplicate_keys_provided(
    valid_platform_config, fakefs
):
    fakefs.create_file(PLATFORM_CONFIG_FILE, contents=yaml.dump(valid_platform_config))

    # Remove the extensions key-value pair from the platform config - re-added as plain text.
    valid_platform_config.pop("extensions")

    duplicate_key = "duplicate-key"
    duplicate_extension = f"""
  {duplicate_key}:
    type: redis
    environments:
      "*":
        engine: '7.1'
        plan: tiny
        apply_immediately: true
"""

    # Combine the valid config (minus the extensions key) and the duplicate key config
    invalid_platform_config = f"""
{yaml.dump(valid_platform_config)}
extensions:
{duplicate_extension}
{duplicate_extension}
"""

    Path(PLATFORM_CONFIG_FILE).write_text(invalid_platform_config)

    linting_failures = lint_yaml_for_duplicate_keys(PLATFORM_CONFIG_FILE)
    assert linting_failures == [
        f'Line 100: duplication of key "{duplicate_key}" in mapping (key-duplicates)'
    ]


def test_validation_fails_if_invalid_default_version_keys_present(
    fakefs, capsys, valid_platform_config
):
    valid_platform_config["default_versions"] = {"something-invalid": "1.2.3"}
    Path(PLATFORM_CONFIG_FILE).write_text(yaml.dump(valid_platform_config))

    with pytest.raises(SystemExit) as ex:
        load_and_validate_platform_config()

        assert "Wrong key 'something-invalid'" in str(ex)


@pytest.mark.parametrize(
    "invalid_key",
    (
        "",
        "invalid-key",
        "platform-helper",  # platform-helper is not valid in the environment overrides.
    ),
)
def test_validation_fails_if_invalid_environment_version_override_keys_present(
    invalid_key, fakefs, capsys, valid_platform_config
):
    valid_platform_config["environments"]["*"]["versions"] = {invalid_key: "1.2.3"}
    Path(PLATFORM_CONFIG_FILE).write_text(yaml.dump(valid_platform_config))

    with pytest.raises(SystemExit) as ex:
        load_and_validate_platform_config()

        assert f"Wrong key '{invalid_key}'" in str(ex)


@pytest.mark.parametrize(
    "invalid_key",
    (
        "",
        "invalid-key",
        "terraform-platform-modules",  # terraform-platform-modules is not valid in the pipeline overrides.
    ),
)
def test_validation_fails_if_invalid_pipeline_version_override_keys_present(
    invalid_key, fakefs, capsys, valid_platform_config
):
    valid_platform_config["environment_pipelines"]["test"]["versions"][invalid_key] = "1.2.3"
    Path(PLATFORM_CONFIG_FILE).write_text(yaml.dump(valid_platform_config))

    with pytest.raises(SystemExit) as ex:
        load_and_validate_platform_config()

        assert f"Wrong key '{invalid_key}'" in str(ex)


def test_load_and_validate_platform_config_fails_with_invalid_yaml(fakefs, capsys):
    """Test that, given the path to an invalid yaml file,
    load_and_validate_config aborts and prints an error."""

    Path(PLATFORM_CONFIG_FILE).write_text("{invalid data")
    with pytest.raises(SystemExit):
        load_and_validate_platform_config()

    assert f"Error: {PLATFORM_CONFIG_FILE} is not valid YAML" in capsys.readouterr().err


def test_validation_runs_against_platform_config_yml(fakefs):
    fakefs.create_file(PLATFORM_CONFIG_FILE, contents='{"application": "my_app"}')

    config = load_and_validate_platform_config()

    assert list(config.keys()) == ["application"]
    assert config["application"] == "my_app"


@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
def test_validation_checks_s3_bucket_names(mock_get_session, s3_extensions_fixture, capfd):
    load_and_validate_platform_config()

    assert "Warning" not in capfd.readouterr().out
    assert mock_get_session.called


@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
def test_aws_validation_can_be_switched_off(mock_get_session, s3_extensions_fixture, capfd):
    load_and_validate_platform_config(disable_aws_validation=True)

    assert "Warning" not in capfd.readouterr().out
    assert not mock_get_session.called


@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
def test_validation_checks_and_warns_for_duplicate_s3_bucket_names(
    mock_get_session, s3_extensions_fixture, capfd
):
    client = mock_aws_client(mock_get_session)
    response = {"Error": {"Code": "403"}}
    client.head_bucket.side_effect = ClientError(response, "HeadBucket")

    load_and_validate_platform_config()

    assert "Warning" in capfd.readouterr().out
    assert mock_get_session.called


@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort")
def test_aws_validation_does_not_warn_for_duplicate_s3_bucket_names_if_aws_validation_off(
    mock_get_session, s3_extensions_fixture, capfd
):
    client = mock_aws_client(mock_get_session)
    response = {"Error": {"Code": "403"}}
    client.head_bucket.side_effect = ClientError(response, "HeadBucket")

    load_and_validate_platform_config(disable_aws_validation=True)

    assert "Warning" not in capfd.readouterr().out
    assert not mock_get_session.called


@patch("dbt_platform_helper.utils.validation.get_aws_session_or_abort", new=Mock())
@patch("dbt_platform_helper.utils.validation.config_file_check")
def test_load_and_validate_platform_config_skips_file_check_when_disable_file_check_parameter_passed(
    mock_config_file_check, capfd, fakefs
):
    fakefs.create_file(PLATFORM_CONFIG_FILE, contents=yaml.dump({"application": "my_app"}))
    load_and_validate_platform_config(disable_file_check=True)

    assert not mock_config_file_check.called


@pytest.mark.parametrize(
    "files, expected_messages",
    [
        (
            [],
            [
                f"`{PLATFORM_CONFIG_FILE}` is missing. Please check it exists and you are in the root directory of your deployment project."
            ],
        ),
        (
            ["storage.yml"],
            [
                f"`storage.yml` is no longer supported. Please move its contents into the `{PLATFORM_CONFIG_FILE}` file under the key 'extensions' and delete `storage.yml`."
            ],
        ),
        (
            ["extensions.yml"],
            [
                f"`extensions.yml` is no longer supported. Please move its contents into the `{PLATFORM_CONFIG_FILE}` file under the key 'extensions' and delete `extensions.yml`."
            ],
        ),
        (
            ["pipelines.yml"],
            [
                f"`pipelines.yml` is no longer supported. Please move its contents into the `{PLATFORM_CONFIG_FILE}` file, change the key 'codebases' to 'codebase_pipelines' and delete `pipelines.yml`."
            ],
        ),
        (
            ["storage.yml", "pipelines.yml"],
            [
                f"`storage.yml` is no longer supported. Please move its contents into the `{PLATFORM_CONFIG_FILE}` file under the key 'extensions' and delete `storage.yml`.",
                f"`pipelines.yml` is no longer supported. Please move its contents into the `{PLATFORM_CONFIG_FILE}` file, change the key 'codebases' to 'codebase_pipelines' and delete `pipelines.yml`.",
            ],
        ),
    ],
)
def test_config_file_check_fails_for_unsupported_files_exist(
    fakefs, capsys, files, expected_messages
):
    for file in files:
        fakefs.create_file(file)

    with pytest.raises(SystemExit):
        config_file_check()

    console_message = capsys.readouterr().out

    for expected_message in expected_messages:
        assert expected_message in console_message


@pytest.mark.parametrize(
    "files, expected_messages",
    [
        (
            [PLATFORM_HELPER_VERSION_FILE],
            [
                f"`{PLATFORM_HELPER_VERSION_FILE}` is no longer supported. "
                f"Please move its contents into the `{PLATFORM_CONFIG_FILE}` file,"
                f" under the key `default_versions: platform-helper:` and delete `{PLATFORM_HELPER_VERSION_FILE}`."
            ],
        ),
    ],
)
def test_config_file_check_warns_if_deprecated_files_exist(
    fakefs, capsys, files, expected_messages
):
    for file in files:
        fakefs.create_file(file)

    config_file_check()

    console_message = capsys.readouterr().out

    for expected_message in expected_messages:
        assert expected_message in console_message


@pytest.mark.parametrize(
    "database_copy_section",
    [
        None,
        [{"from": "dev", "to": "test"}],
        [{"from": "test", "to": "dev"}, {"from": "prod", "to": "test"}],
    ],
)
def test_validate_database_copy_section_success_cases(database_copy_section):
    config = {
        "application": "test-app",
        "environments": {"dev": {}, "test": {}, "prod": {}},
        "extensions": {
            "our-postgres": {
                "type": "postgres",
                "version": 7,
            }
        },
    }

    if database_copy_section:
        config["extensions"]["our-postgres"]["database_copy"] = database_copy_section

    validate_database_copy_section(config)

    # Should get here fine if the config is valid.


@pytest.mark.parametrize(
    "database_copy_section, expected_parameters",
    [
        ([{"from": "hotfix", "to": "test"}], ["from"]),
        ([{"from": "dev", "to": "hotfix"}], ["to"]),
        ([{"from": "hotfix", "to": "hotfix"}], ["to", "from"]),
        ([{"from": "test", "to": "dev"}, {"from": "dev", "to": "hotfix"}], ["to"]),
        ([{"from": "hotfix", "to": "test"}, {"from": "dev", "to": "test"}], ["from"]),
    ],
)
def test_validate_database_copy_section_failure_cases(
    capfd, database_copy_section, expected_parameters
):
    config = {
        "application": "test-app",
        "environments": {"dev": {}, "test": {}, "prod": {}},
        "extensions": {
            "our-postgres": {
                "type": "postgres",
                "version": 7,
            }
        },
    }

    config["extensions"]["our-postgres"]["database_copy"] = database_copy_section

    with pytest.raises(SystemExit):
        validate_database_copy_section(config)

    console_message = capfd.readouterr().err

    for param in expected_parameters:
        msg = f"database_copy '{param}' parameter must be a valid environment (dev, test, prod) but was 'hotfix' in extension 'our-postgres'."
        assert msg in console_message


def test_validate_database_copy_fails_if_from_and_to_are_the_same(capfd):
    config = {
        "application": "test-app",
        "environments": {"dev": {}, "test": {}, "prod": {}},
        "extensions": {
            "our-postgres": {
                "type": "postgres",
                "version": 7,
                "database_copy": [{"from": "dev", "to": "dev"}],
            }
        },
    }

    with pytest.raises(SystemExit):
        validate_database_copy_section(config)

    console_message = capfd.readouterr().err

    msg = (
        f"database_copy 'to' and 'from' cannot be the same environment in extension 'our-postgres'."
    )
    assert msg in console_message


@pytest.mark.parametrize(
    "env_name",
    ["prod", "prod-env", "env-that-is-prod", "thing-prod-thing"],
)
def test_validate_database_copy_section_fails_if_the_to_environment_is_prod(capfd, env_name):
    config = {
        "application": "test-app",
        "environments": {"dev": {}, "test": {}, "prod": {}},
        "extensions": {
            "our-postgres": {
                "type": "postgres",
                "version": 7,
                "database_copy": [{"from": "dev", "to": env_name}],
            }
        },
    }

    with pytest.raises(SystemExit):
        validate_database_copy_section(config)

    console_message = capfd.readouterr().err

    msg = f"Copying to a prod environment is not supported: database_copy 'to' cannot be '{env_name}' in extension 'our-postgres'."
    assert msg in console_message


def test_validate_database_copy_multi_postgres_success():
    config = {
        "application": "test-app",
        "environments": {"dev": {}, "test": {}, "prod": {}},
        "extensions": {
            "our-postgres": {
                "type": "postgres",
                "version": 7,
                "database_copy": [{"from": "dev", "to": "test"}],
            },
            "our-other-postgres": {
                "type": "postgres",
                "version": 7,
                "database_copy": [{"from": "dev", "to": "test"}, {"from": "prod", "to": "dev"}],
            },
        },
    }

    validate_database_copy_section(config)

    # Should get here fine if the config is valid.


def test_validate_database_copy_multi_postgres_failures(capfd):
    config = {
        "application": "test-app",
        "environments": {"dev": {}, "test": {}, "prod": {}},
        "extensions": {
            "our-postgres": {
                "type": "postgres",
                "version": 7,
                "database_copy": [{"from": "devvv", "to": "test"}],
            },
            "our-other-postgres": {
                "type": "postgres",
                "version": 7,
                "database_copy": [{"from": "test", "to": "test"}, {"from": "dev", "to": "prod"}],
            },
        },
    }

    with pytest.raises(SystemExit):
        validate_database_copy_section(config)

    console_message = capfd.readouterr().err

    assert (
        f"database_copy 'from' parameter must be a valid environment (dev, test, prod) but was 'devvv' in extension 'our-postgres'."
        in console_message
    )
    assert (
        f"database_copy 'to' and 'from' cannot be the same environment in extension 'our-other-postgres'."
        in console_message
    )
    assert (
        f"Copying to a prod environment is not supported: database_copy 'to' cannot be 'prod' in extension 'our-other-postgres'."
        in console_message
    )
