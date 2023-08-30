import json
from pathlib import Path

import jsonschema
import pytest
import yaml
from jsonschema import validate

PROJECT_ROOT = Path(__file__).parent.parent

with open(PROJECT_ROOT / "commands/addon-plans.yml") as fd:
    plans = yaml.safe_load(fd)

with open(PROJECT_ROOT / "commands/schemas/addons-schema.json") as fd:
    schema = json.load(fd)


def expect_jsonschema_validation_error(addon):
    try:
        validate(instance=addon, schema=schema)
    except jsonschema.exceptions.ValidationError as err:
        return err.message
    return False


def test_require_valid_type():
    addon = yaml.safe_load(
        """
mys3bucket:
    type: not-valid
""",
    )

    assert (
        expect_jsonschema_validation_error(addon)
        == "'not-valid' is not one of ['rds-postgres', 'aurora-postgres', 'redis', 'opensearch', 's3', 's3-policy', 'appconfig-ipfilter']"
    )


@pytest.mark.parametrize(
    "addon_type",
    [
        "s3",
        "s3-policy",
        "redis",
        "opensearch",
        "rds-postgres",
        "aurora-postgres",
    ],
)
def test_extrakeys_not_allowed(addon_type):
    addon = yaml.safe_load(
        f"""
mys3bucket:
    type: {addon_type}
    an-extra-key: "something"
""",
    )

    assert expect_jsonschema_validation_error(addon)


@pytest.mark.parametrize(
    "addon_type",
    [
        "s3",
        "s3-policy",
        "redis",
        "opensearch",
        "rds-postgres",
    ],
)
def test_environment_extrakeys_not_allowed(addon_type):
    addon = yaml.safe_load(
        f"""
addonitem:
    type: {addon_type}
    environments:
        default:
            an-extra-key: "something"
""",
    )

    assert (
        expect_jsonschema_validation_error(addon)
        == "Additional properties are not allowed ('an-extra-key' was unexpected)"
    )


@pytest.mark.parametrize(
    "bucket_name",
    [
        "a",  # less than 3 chars
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",  # 64 chars
        "a$aaa",  # invalid chars
        "_asdf",  # must begin/end with alphanumeric
    ],
)
def test_s3_bucketname_validation(bucket_name):
    addon = yaml.safe_load(
        f"""
mys3bucket:
    type: s3

    bucket-name: "{bucket_name}"
""",
    )

    assert expect_jsonschema_validation_error(addon)


@pytest.mark.parametrize(
    "addon_yaml, validation_message",
    [
        (
            """
myredis:
    type: redis
    environments:
        prod:
            instance: invalid-instance
""",
            "'invalid-instance' is not one of",
        ),
        (
            """
myredis:
    type: redis
    environments:
        prod:
            plan: invalid-plan
""",
            "'invalid-plan' is not one of",
        ),
        (
            """
myredis:
    type: redis
    environments:
        prod:
            engine: invalid-engine
""",
            "'invalid-engine' is not one of",
        ),
        (
            """
myredis:
    type: redis
    environments:
        prod:
            replicas: 6
""",
            "6 is greater than the maximum of 5",
        ),
    ],
)
def test_redis_invalid_input(addon_yaml, validation_message):
    addon = yaml.safe_load(addon_yaml)

    assert validation_message in expect_jsonschema_validation_error(addon)


@pytest.mark.parametrize(
    "addon_yaml, validation_message",
    [
        (
            """
mypostgres:
    type: rds-postgres
    environments:
        prod:
            instance: invalid-instance
""",
            "'invalid-instance' is not one of",
        ),
        (
            """
mypostgres:
    type: rds-postgres
    environments:
        prod:
            plan: invalid-plan
""",
            "'invalid-plan' is not one of",
        ),
        (
            """
mypostgres:
    type: rds-postgres
    environments:
        prod:
            replicas: 6
""",
            "6 is greater than the maximum of 5",
        ),
        (
            """
mypostgres:
    type: rds-postgres
    environments:
        prod:
            volume-size: 100001
""",
            "100001 is greater than the maximum of 10000",
        ),
    ],
)
def test_postgres_invalid_input(addon_yaml, validation_message):
    addon = yaml.safe_load(addon_yaml)

    assert validation_message in expect_jsonschema_validation_error(addon)


@pytest.mark.parametrize(
    "addon_yaml, validation_message",
    [
        (
            """
myaurora:
    type: aurora-postgres
    version: 1.2
    environments:
        prod:
            min-capacity: -1
""",
            "-1 is less than the minimum of 0",
        ),
        (
            """
myaurora:
    type: aurora-postgres
    version: 1.2
    environments:
        prod:
            max-capacity: 0
""",
            "0 is less than the minimum of 0.5",
        ),
    ],
)
def test_aurora_invalid_input(addon_yaml, validation_message):
    addon = yaml.safe_load(addon_yaml)

    assert validation_message in expect_jsonschema_validation_error(addon)


@pytest.mark.parametrize(
    "addon_yaml, validation_message",
    [
        (
            """
myopensearch:
    type: opensearch
    environments:
        prod:
            instance: invalid-instance
""",
            "'invalid-instance' is not one of",
        ),
        (
            """
myopensearch:
    type: opensearch
    environments:
        prod:
            plan: invalid-plan
""",
            "'invalid-plan' is not one of",
        ),
        (
            """
myopensearch:
    type: opensearch
    environments:
        prod:
            replicas: 6
""",
            "6 is greater than the maximum of 5",
        ),
    ],
)
def test_opensearch_invalid_input(addon_yaml, validation_message):
    addon = yaml.safe_load(addon_yaml)

    assert validation_message in expect_jsonschema_validation_error(addon)


def test_s3_valid_example():
    addon = yaml.safe_load(
        """
mys3bucket:
    type: s3

    bucket-name: "mys3bucket"
    readonly: true
    services:
        - web
        - web-celery
        - proxy

    environments:
        prod:
            bucket-name: "bucket-name"

        dev:
            bucket-name: "bucket-name"
""",
    )

    validate(instance=addon, schema=schema)


def test_s3_policy_valid_example():
    addon = yaml.safe_load(
        """
mys3bucket:
    type: s3-policy

    bucket-name: "mys3bucket"
    readonly: true
    services:
        - web
        - web-celery
        - proxy

    environments:
        prod:
            bucket-name: "bucket-name"

        dev:
            bucket-name: "bucket-name"
""",
    )

    validate(instance=addon, schema=schema)


def test_redis_valid_example():
    addon = yaml.safe_load(
        """
myredis:
    type: redis
    environments:
        default:
            plan: large

        prod:
            engine: '6.2'
            instance: cache.m6g.large
            replicas: 2
""",
    )

    validate(instance=addon, schema=schema)


def test_opensearch_valid_example():
    addon = yaml.safe_load(
        """
myopensearch:
    type: opensearch
    environments:
        default:
            plan: medium-ha

        prod:
            replicas: 1
            instance: m6g.2xlarge.search
""",
    )

    validate(instance=addon, schema=schema)


def test_postgres_valid_example():
    addon = yaml.safe_load(
        """
mypostgres:
    type: rds-postgres
    environments:
        default:
            plan: medium-13-ha

        prod:
            instance: db.m5.4xlarge
            volume-size: 500
            replicas: 3
""",
    )

    validate(instance=addon, schema=schema)


def test_aurora_valid_example():
    addon = yaml.safe_load(
        """
mypostgres:
    type: aurora-postgres
    version: 1.2
    environments:
        default:
            min-capacity: 0.5
            max-capacity: 35
""",
    )

    validate(instance=addon, schema=schema)


def test_schema_opensearch_plans_match_available_plans():
    assert set(schema["definitions"]["opensearch-plans"]["enum"]) == set(plans["opensearch"].keys())


def test_schema_redis_plans_match_available_plans():
    assert set(schema["definitions"]["redis-plans"]["enum"]) == set(plans["redis"].keys())


def test_schema_postgres_plans_match_available_plans():
    assert set(schema["definitions"]["rds-postgres-plans"]["enum"]) == set(
        plans["rds-postgres"].keys()
    )
