import re
from pathlib import Path

import pytest
from schema import SchemaError

from dbt_copilot_helper.utils.validation import float_between_with_halfstep
from dbt_copilot_helper.utils.validation import int_between
from dbt_copilot_helper.utils.validation import validate_addons
from dbt_copilot_helper.utils.validation import validate_string
from tests.copilot_helper.conftest import UTILS_FIXTURES_DIR


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


@pytest.fixture()
def addons_fixtures_path():
    return Path(UTILS_FIXTURES_DIR / "addons_files")


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
    ],
)
def test_validate_addons_success(addons_fixtures_path, addons_file):
    errors = validate_addons(addons_fixtures_path / addons_file)

    assert len(errors) == 0


@pytest.mark.parametrize(
    "addons_file, exp_error",
    [
        (
            "s3_addons_bad_data.yml",
            {
                "my-s3-bucket-1": r"readonly.*should be instance of 'bool'",
                "my-s3-bucket-2": r"deletion-policy.*does not match 'Retrain'",
                "my-s3-bucket-3": r"services.*should be instance of 'list'",
                "my-s3-bucket-4": r"services.*should be instance of 'str'",
                "my-s3-bucket-5": r"environments.*dev.*bucket-name.*does not match 'banana-s3alias'",
                "my-s3-bucket-6": r"environments.*dev.*deletion-policy.*does not match False",
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
                "my-s3-bucket-policy-2": r"deletion-policy.*does not match 'Retrain'",
                "my-s3-bucket-policy-3": r"services.*should be instance of 'list'",
                "my-s3-bucket-policy-4": r"services.*should be instance of 'str'",
                "my-s3-bucket-policy-5": r"environments.*dev.*bucket-name.*does not match 'banana-s3alias'",
                "my-s3-bucket-policy-6": r"environments.*dev.*deletion-policy.*does not match False",
                "my-s3-bucket-policy-7": r"Wrong key 'unknown1'",
                "my-s3-bucket-policy-8": r"Wrong key 'objects'",
                "my-s3-bucket-policy-9": r"environments.*Wrong key 'unknown3'",
            },
        ),
        (
            "aurora_addons_bad_data.yml",
            {
                "my-aurora-db-1": r"Missing key: 'version'",
                "my-aurora-db-2": r"deletion-policy.*does not match 'None'",
                "my-aurora-db-3": r"deletion-protection.*should be instance of 'bool'",
                "my-aurora-db-4": r"environments.*Missing key: <class 'str'>",
                "my-aurora-db-5": r"environments.*default.*min-capacity.*should be a number between 0.5 and 128 in half steps",
                "my-aurora-db-6": r"environments.*default.*max-capacity.*should be a number between 0.5 and 128 in half steps",
                "my-aurora-db-7": r"environments.*default.*snapshot-id.*should be instance of 'str'",
                "my-aurora-db-8": r"environments.*default.*deletion-protection.*should be instance of 'bool'",
                "my-aurora-db-9": r"environments.*default.*deletion-policy.*does not match 'Slapstick'",
                "my-aurora-db-10": r"Wrong key 'bad-key'",
                "my-aurora-db-11": r"environments.*default.*Wrong key 'bad-env-key'",
            },
        ),
        (
            "rds_addons_bad_data.yml",
            {
                "my-rds-db-1": r"Wrong key 'im-invalid' in",
                "my-rds-db-2": r"Missing key: 'version'",
                "my-rds-db-3": r"did not validate 77",
                "my-rds-db-4": r"'whatever' should be instance of 'bool'",
                "my-rds-db-5": r"'environments'.*'default'.*'plan'.*does not match 'cunning'",
                "my-rds-db-6": r"'environments'.*'default'.*'instance'.*does not match 'a-wee-little-one'",
                "my-rds-db-7a": r"environments'.*'default'.*'volume-size'.*should be an int between 5 and 10000",
                "my-rds-db-7b": r"environments'.*'default'.*'volume-size'.*should be an int between 5 and 10000",
                "my-rds-db-7c": r"environments'.*'default'.*'volume-size'.*should be an int between 5 and 10000",
                "my-rds-db-8a": r"environments'.*'default'.*'replicas'.*should be an int between 0 and 5",
                "my-rds-db-8b": r"environments'.*'default'.*'replicas'.*should be an int between 0 and 5",
                "my-rds-db-9": r"'environments'.*'default'.*snapshot-id.*False should be instance of 'str'",
                "my-rds-db-10": r"'environments'.*'default'.*deletion-policy.*'Snapshot' does not match 'None'",
                "my-rds-db-11": r"'environments'.*'default'.*deletion-protection.*12 should be instance of 'bool'",
            },
        ),
        (
            "redis_addons_bad_data.yml",
            {
                "my-redis-1": r"Wrong key 'bad-key' in",
                "my-redis-2": r"deletion-policy.*Snapshot' does not match 'Disabled'",
                "my-redis-3": r"environments.*default.*engine.*'6.2' does not match 'a-big-engine'",
                "my-redis-4": r"environments.*default.*plan.*does not match 'enormous'",
                "my-redis-5": r"environments.*default.*replicas.*should be an int between 0 and 5",
                "my-redis-6": r"environments.*default.*instance.*does not match 'teeny'",
                "my-redis-7": r"environments.*default.*deletion-policy.*does not match 'Never'",
            },
        ),
        (
            "opensearch_addons_bad_data.yml",
            {
                "my-opensearch-1": r"Wrong key 'nonsense' in",
                "my-opensearch-2": r"deletion-policy.*does not match 27",
                "my-opensearch-3": r"environments.*False should be instance of 'dict'",
                "my-opensearch-4": r"environments.*Wrong key 'opensearch-plan'",
                "my-opensearch-5": r"environments.*dev.*plan.*does not match 'largish'",
                "my-opensearch-6": r"environments.*dev.*replicas.*should be an int between 0 and 5",
                "my-opensearch-7": r"environments.*dev.*instance.*does not match 'medium'",
                "my-opensearch-8": r"environments.*dev.*engine.*does not match 7.3",
                "my-opensearch-9": r"environments.*dev.*volume_size.*should be an int between 10 and 511",
                "my-opensearch-10": r"environments.*dev.*volume_size.*should be an int between 10 and 511",
                "my-opensearch-11": r"environments.*dev.*deletion-policy.*does not match 'Snapeshot'",
            },
        ),
        (
            "monitoring_addons_bad_data.yml",
            {
                "my-monitoring-1": r"Wrong key 'monitoring-param' in",
                "my-monitoring-2": r"environments.*'prod' should be instance of 'dict'",
                "my-monitoring-3": r"environments.*default.*should be instance of 'dict'",
                "my-monitoring-4": r"environments.*default.*enable-ops-center.* should be instance of 'bool'",
            },
        ),
    ],
)
def test_validate_addons_failure(addons_fixtures_path, addons_file, exp_error):
    error_map = validate_addons(addons_fixtures_path / addons_file)
    for entry, error in exp_error.items():
        assert entry in error_map
        assert bool(re.search(f"(?s)Error in {entry}:.*{error}", error_map[entry]))


def test_validate_addons_unsupported_addon(addons_fixtures_path):
    error_map = validate_addons(addons_fixtures_path / "unsupported_addon.yml")
    for entry, error in error_map.items():
        assert "Unsupported addon type 'unsupported_addon' in addon 'my-unsupported-addon'" == error


def test_validate_addons_missing_type(addons_fixtures_path):
    error_map = validate_addons(addons_fixtures_path / "missing_type_addon.yml")
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
        assert ex.code == "should be an int between 1 and 9"


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
        assert ex.code == "should be a number between 0.5 and 128 in half steps"
