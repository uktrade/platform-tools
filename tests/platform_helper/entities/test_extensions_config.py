import re
from pathlib import Path

import yaml
from schema import SchemaError

from dbt_platform_helper.entities.platform_config_schema import PlatformConfigSchema
from tests.platform_helper.conftest import INPUT_DATA_DIR

os_schema = PlatformConfigSchema.extension_schemas().get("opensearch", None)
modes = ("schema", "pydantic")


def _get_validator(extension, param):
    if param == "schema":
        from dbt_platform_helper.entities.platform_config_schema import (
            PlatformConfigSchema,
        )

        return PlatformConfigSchema.extension_schemas()[extension].validate
    if param == "pydantic":
        from dbt_platform_helper.entities.platform import validate_extension_fn

        return validate_extension_fn(extension)


def make_validator_fixture(extension, mode):
    return _get_validator(extension, mode)


def test_validate_opensearch_success():

    for mode in modes:
        with open(Path(INPUT_DATA_DIR / "platform/config/extensions") / "opensearch.yml") as fh:
            opensearch_exts = yaml.safe_load(fh)
            for ext, config in opensearch_exts.items():
                validator = make_validator_fixture("opensearch", mode)
                validator(config)


def test_validate_opensearch_failure():
    errors = {}
    exp_error = {
        "my-opensearch-bad-param": {
            "schema": r"Wrong key 'nonsense' in",
            "pydantic": r"Wrong key 'nonsense' in",
        },
        "my-opensearch-environments-should-be-list": {
            "schema": r"environments.*False should be instance of 'dict'",
            "pydantic": r"Input should be a valid dictionary",
        },
        "my-opensearch-bad-env-param": {
            "schema": r"environments.*Wrong key 'opensearch_plan'",
            "pydantic": r"Wrong key 'opensearch_plan' in",
        },
        "my-opensearch-bad-plan": {
            "schema": r"environments.*dev.*plan.*does not match 'largish'",
            "pydantic": r"environments.* Input should be",
        },
        "my-opensearch-no-plan": {
            "schema": r"Missing key: 'plan'",
            "pydantic": r"Missing key: 'plan'",
        },
        "my-opensearch-volume-size-too-small": {
            "schema": r"environments.*dev.*volume_size.*should be an integer greater than 10",
            "pydantic": r"environments.*dev.*volume_size.*should be an integer greater than 10",
        },
        "my-opensearch-invalid-size-for-small": {
            "schema": r"environments.*dev.*volume_size.*should be an integer between 10 and [0-9]{2,4}.* for plan.*",
            "pydantic": r"environments.*dev.*volume_size.*should be an integer between 10 and [0-9]{2,4}.* for plan.*",
        },
        "my-opensearch-invalid-size-for-large": {
            "schema": r"environments.*production.*volume_size.*should be an integer between 10 and [0-9]{2,4}.* for plan.*",
            "pydantic": r"environments.*production.*volume_size.*should be an integer between 10 and [0-9]{2,4}.* for plan.*",
        },
        "my-opensearch-invalid-deletion-policy": {
            "schema": r"environments.*dev.*deletion_policy.*does not match 'Snapshot'",
            "pydantic": r"environments.*dev.*deletion_policy.*Input should be 'Delete' or 'Retain' ",
        },
        "my-opensearch-instances-should-be-int": {
            "schema": r"environments.*instances.*should be instance of 'int'",
            "pydantic": r"environments.*instances.*Input should be a valid integer, unable to parse string as an integer",
        },
        "my-opensearch-master-should-be-bool": {
            "schema": r"environments.*master.*should be instance of 'bool'",
            "pydantic": r"'yes' should be instance of 'bool'",
        },
        "my-opensearch-es-app-log-retention-in-days-should-be-int": {
            "schema": r"environments.*es_app_log_retention_in_days.*should be instance of 'int'",
            "pydantic": r"True should be instance of 'int'",
        },
        "my-opensearch-index-slow-log-retention-in-days-should-be-int": {
            "schema": r"environments.*index_slow_log_retention_in_days.*should be instance of 'int'",
            "pydantic": r"True should be instance of 'int'",
        },
        "my-opensearch-audit-log-retention-in-days-should-be-int": {
            "schema": r"environments.*audit_log_retention_in_days.*should be instance of 'int'",
            "pydantic": r"True should be instance of 'int'",
        },
        "my-opensearch-search-slow-log-retention-in-days-should-be-int": {
            "schema": r"environments.*search_slow_log_retention_in_days.*should be instance of 'int'",
            "pydantic": r"True should be instance of 'int'",
        },
        "my-opensearch-password-special-characters": {
            "schema": r"environments.*password_special_characters.*should be instance of 'str'",
            "pydantic": r"environments.*password_special_characters.*Input should be a valid string",
        },
        "my-opensearch-urlencode-password": {
            "schema": r"environments.*urlencode_password.*should be instance of 'bool'",
            "pydantic": r"environments.*urlencode_password.*Input should be a valid boolean, unable to interpret input",
        },
        "my-opensearch-bad-user-vpc-endpoint": {
            "schema": r"environments.*dev.*external_user_access.*user-write-access.vpc_endpoint_id.*must be a valid Opensearch VPC Endpoint ID",
            "pydantic": r"environments.*dev.*external_user_access.*user-write-access.vpc_endpoint_id.*must be a valid Opensearch VPC Endpoint ID",
        },
        "my-opensearch-bad-user-account": {
            "schema": r"environments.*dev.*external_user_access.*user-write-access.account.*must be a valid AWS 12 Digit Account Number",
            "pydantic": r"environments.*dev.*external_user_access.*user-write-access.account.*must be a valid AWS 12 Digit Account Number",
        },
        "my-opensearch-bad-user-read": {
            "schema": r"environments.*dev.*external_user_access.*user-write-access.read.*Input should be a valid boolean",
            "pydantic": r"environments.*dev.*external_user_access.*user-write-access.read.*Input should be a valid boolean",
        },
        "my-opensearch-bad-user-write": {
            "schema": r"environments.*dev.*external_user_access.*user-write-access.write.*Input should be a valid boolean",
            "pydantic": r"environments.*dev.*external_user_access.*user-write-access.write.*Input should be a valid boolean",
        },
        "my-opensearch-bad-user-cyber": {
            "schema": r"environments.*dev.*external_user_access.*user-write-access.cyber_sign_off.*must contain a valid DBT email address",
            "pydantic": r"environments.*dev.*external_user_access.*user-write-access.cyber_sign_off.*must contain a valid DBT email address",
        },
    }
    for mode in modes:
        print(mode)
        with open(
            Path(INPUT_DATA_DIR / "platform/config/extensions") / "opensearch_bad_data.yml"
        ) as fh:
            opensearch_exts = yaml.safe_load(fh)

            for ext, config in opensearch_exts.items():
                try:
                    validator = make_validator_fixture("opensearch", mode)
                    print(config)
                    validator(config)
                except SchemaError as ex:
                    errors[ext] = ex.code

        for entry, error in exp_error.items():
            assert errors.get(entry), f"{mode}:{entry}: {error} not found in produced errors"
            assert bool(
                re.search(f"(?s).*{error[mode]}", errors[entry])
            ), f"""
            for: {entry}
            regex: {error[mode]} 
            could not find match in:
            {errors[entry]}

            """
