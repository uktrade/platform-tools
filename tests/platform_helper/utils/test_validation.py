import re
from pathlib import Path

import pytest
import yaml
from schema import SchemaError

from dbt_platform_helper.providers.platform_config_schema import PlatformConfigSchema
from dbt_platform_helper.utils.validation import validate_addons
from tests.platform_helper.conftest import UTILS_FIXTURES_DIR


def load_addons(addons_file):
    with open(Path(UTILS_FIXTURES_DIR / "addons_files") / addons_file) as fh:
        return yaml.safe_load(fh)


@pytest.mark.parametrize(
    "regex_pattern, valid_strings, invalid_strings",
    [
        (r"^\d+-\d+$", ["1-10"], ["20-21-23"]),
        (r"^\d+s$", ["10s"], ["10seconds"]),
        (
            # Todo: Make this actually validate a git branch name properly; https://git-scm.com/docs/git-check-ref-format
            r"^((?!\*).)*(\*)?$",
            ["test/valid/branch", "test/valid/branch*", "test/valid/branch-other"],
            ["test*invalid/branch", "test*invalid/branch*"],
        ),
    ],
)
def test_validate_string(regex_pattern, valid_strings, invalid_strings):
    validator = PlatformConfigSchema.string_matching_regex(regex_pattern)

    for valid_string in valid_strings:
        assert validator(valid_string) == valid_string

    for invalid_string in invalid_strings:
        with pytest.raises(SchemaError) as err:
            validator(invalid_string)

        assert (
            err.value.args[0]
            == f"String '{invalid_string}' does not match the required pattern '{regex_pattern}'."
        )


@pytest.mark.parametrize(
    "addons_file",
    [
        "s3_addons.yml",
        "s3_policy_addons.yml",
        "postgres_addons.yml",
        "redis_addons.yml",
        "opensearch_addons.yml",
        "monitoring_addons.yml",
        "no_param_addons.yml",
        "alb_addons.yml",
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
                "my-s3-external-access-bucket-invalid-arn": r"role_arn must contain a valid ARN for an IAM role",
                "my-s3-external-access-bucket-invalid-email": r"cyber_sign_off_by must contain a valid DBT email address",
                "my-s3-cross-environment-service-access-bucket-invalid-environment": r"Environment name hyphen-not-allowed-in-environment is invalid",
                "my-s3-cross-environment-service-access-bucket-invalid-email": r"cyber_sign_off_by must contain a valid DBT email address",
                "my-s3-cross-environment-service-access-bucket-missing-environment": r"Missing key: 'environment'",
                "my-s3-cross-environment-service-access-bucket-missing-account": r"Missing key: 'account'",
                "my-s3-cross-environment-service-access-bucket-missing-service": r"Missing key: 'service'",
                "my-s3-cross-environment-service-access-bucket-invalid-write": r"cross_environment_service_access.*'WRITE' should be instance of 'bool'",
                "my-s3-cross-environment-service-access-bucket-invalid-read": r"cross_environment_service_access.*'READ' should be instance of 'bool'",
                "my-s3-cross-environment-service-access-bucket-missing-cyber-sign-off": r"Missing key: 'cyber_sign_off_by'",
            },
        ),
        (
            "s3_policy_addons_bad_data.yml",
            {
                "my-s3-bucket-policy-services-should-be-list": r"services.*should be instance of 'list'",
                "my-s3-bucket-policy-service-should-be-string": r"services.*should be instance of 'str'",
                "my-s3-bucket-policy-bad-name-suffix": r"Bucket name 'banana-s3alias' is invalid:\n  Names cannot be suffixed '-s3alias'",
                "my-s3-bucket-policy-invalid-param": r"Wrong key 'unknown1'",
                "my-s3-bucket-policy-invalid-object-param": r"Wrong key 'objects'",
                "my-s3-bucket-policy-invalid-env-param": r"environments.*Wrong key 'unknown3'",
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
                "my-rds-data-migration-schedule-should-be-a-string": r"'database_copy.*False should be instance of 'str'",
            },
        ),
        (
            "redis_addons_bad_data.yml",
            {
                "my-redis-bad-key": r"Wrong key 'bad_key' in",
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
            "datadog_addons_bad_data.yml",
            {
                "my-datadog-bad-key": r"Wrong key 'bad_key' in",
                "my-datadog-bad-team-name": r"'environments'.*'default'.*team_name.*should be instance of 'str'",
                "my-datadog-bad-contact-name": r"'environments'.*'default'.*contact_name.*should be instance of 'str'",
                "my-datadog-bad-contact-email": r"'environments'.*'default'.*contact_email.*should be instance of 'str'",
                "my-datadog-bad-repository": r"'environments'.*'default'.*repository.*should be instance of 'str'",
                "my-datadog-bad-docs": r"'environments'.*'default'.*docs.*should be instance of 'str'",
                "my-datadog-bad-services-to-monitor": r"'environments'.*'default'.*services_to_monitor.*should be instance of 'list'",
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
                "my-alb-cdn-timeout-seconds-should-be-an-int": r"environments.*dev.*should be instance of 'int'",
                "my-alb-default-waf-should-be-a-string": r"environments.*dev.*should be instance of 'str'",
                "my-alb-enable-logging-should-be-a-bool": r"environments.*dev.*should be instance of 'bool'",
                "my-alb-forwarded-values-forward-should-be-a-string": r"environments.*dev.*should be instance of 'str'",
                "my-alb-forwarded-values-headers-should-be-a-list": r"environments.*dev.*should be instance of 'list'",
                "my-alb-forwarded-values-query-string-should-be-a-bool": r"environments.*dev.*should be instance of 'bool'",
                "my-alb-origin-protocol-policy-should-be-a-string": r"environments.*dev.*should be instance of 'str'",
                "my-alb-origin-ssl-protocols-should-be-a-list": r"environments.*dev.*should be instance of 'list'",
                "my-alb-slack-alert-channel-alb-secret-rotation-should-be-a-string": r"environments.*dev.*should be instance of 'str'",
                "my-alb-viewer-certificate-minimum-protocol-version-should-be-a-string": r"environments.*dev.*should be instance of 'str'",
                "my-alb-viewer-certificate-ssl-support-method-should-be-a-string": r"environments.*dev.*should be instance of 'str'",
                "my-alb-view-protocol-policy-should-be-a-string": r"environments.*dev.*should be instance of 'str'",
                "my-alb-cache-policy-min-ttl-should-be-a-int": r"environments.*dev.*should be instance of 'int'",
                "my-alb-cache-policy-max-ttl-should-be-a-int": r"environments.*dev.*should be instance of 'int'",
                "my-alb-cache-policy-default-ttl-should-be-a-int": r"environments.*dev.*should be instance of 'int'",
                "my-alb-cache-policy-cookies-config-should-be-a-string": r"environments.*dev.*did not validate",
                "my-alb-cache-policy-cookies-list-should-be-a-list": r"environments.*dev.*should be instance of 'list'",
                "my-alb-cache-policy-header-should-be-a-string": r"environments.*dev.*did not validate",
                "my-alb-cache-policy-headers-list-should-be-a-list": r"environments.*dev.*should be instance of 'list'",
                "my-alb-cache-policy-query-string-behavior-should-be-a-string": r"environments.*dev.*did not validate",
                "my-alb-cache-policy-cache-policy-query-strings-should-be-a-list": r"environments.*dev.*should be instance of 'list'",
                "my-alb-origin-request-policy-should-be-a-dict": r"environments.*dev.*should be instance of 'dict'",
                "my-alb-paths-default-cache-should-be-a-string": r"environments.*dev.*should be instance of 'str'",
                "my-alb-paths-default-request-should-be-a-string": r"environments.*dev.*should be instance of 'str'",
                "my-alb-paths-additional-should-be-a-list": r"Key 'additional' error.*False should be instance of 'list'",
            },
        ),
    ],
)
def test_validate_addons_failure(
    addons_file,
    exp_error,
):
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
    assert PlatformConfigSchema.is_integer_between(1, 9)(value)


@pytest.mark.parametrize("value", [-1, 10])
def test_between_raises_error(value):
    try:
        PlatformConfigSchema.is_integer_between(1, 9)(value)
        assert False, f"testing that {value} is between 1 and 9 failed to raise an error."
    except SchemaError as ex:
        assert ex.code == "should be an integer between 1 and 9"


@pytest.mark.parametrize("bucket_name", ["abc", "a" * 63, "abc-123.xyz", "123", "257.2.2.2"])
def test_validate_s3_bucket_name_success_cases(bucket_name):
    assert PlatformConfigSchema.valid_s3_bucket_name(bucket_name)


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
    exp_error = f"Bucket name '{bucket_name}' is invalid:\n  {error_message}"
    with pytest.raises(SchemaError) as ex:
        PlatformConfigSchema.valid_s3_bucket_name(bucket_name)

    assert exp_error in str(ex.value)


def test_validate_s3_bucket_name_multiple_failures():
    bucket_name = "xn--one-two..THREE" + "z" * 50 + "--ol-s3"
    with pytest.raises(SchemaError) as ex:
        PlatformConfigSchema.valid_s3_bucket_name(bucket_name)

    exp_errors = [
        "Length must be between 3 and 63 characters inclusive.",
        "Names can only contain the characters 0-9, a-z, '.' and '-'.",
        "Names cannot contain two adjacent periods.",
        "Names cannot be prefixed 'xn--'.",
        "Names cannot be suffixed '--ol-s3'.",
    ]
    for exp_error in exp_errors:
        assert exp_error in str(ex.value)
