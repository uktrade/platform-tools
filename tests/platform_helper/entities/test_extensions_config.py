import re
from pathlib import Path

import yaml
from schema import SchemaError

from dbt_platform_helper.entities.platform_config_schema import PlatformConfigSchema
from tests.platform_helper.conftest import EXPECTED_DATA_DIR
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

    with open(
        EXPECTED_DATA_DIR / "platform/config" / "extensions" / "opensearch_bad_data.yml"
    ) as ee:
        exp_error = yaml.safe_load(ee)

    for mode in modes:
        with open(
            Path(INPUT_DATA_DIR / "platform/config/extensions") / "opensearch_bad_data.yml"
        ) as fh:
            opensearch_exts = yaml.safe_load(fh)

            for ext, config in opensearch_exts.items():
                try:
                    validator = make_validator_fixture("opensearch", mode)
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
