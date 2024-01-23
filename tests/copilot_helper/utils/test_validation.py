import re
from pathlib import Path

import pytest
from schema import SchemaError

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
    ["s3_addons.yml"],
)
def test_validate_addons_success(addons_fixtures_path, addons_file):
    validate_addons(addons_fixtures_path / addons_file)


@pytest.mark.parametrize(
    "addons_file, exp_error",
    [
        ("s3_addons_bad_property.yml", {"my-s3-bucket": r"Wrong key 'ennvironments' in"}),
        (
            "s3_addons_bad_value.yml",
            {
                "my-s3-bucket-with-an-object": r"Key 'services' error:\s*33 should be instance of 'list'"
            },
        ),
    ],
)
def test_validate_addons_failure(addons_fixtures_path, addons_file, exp_error):
    error_map = validate_addons(addons_fixtures_path / addons_file)
    for entry, error in error_map.items():
        assert bool(re.search(exp_error[entry], error))
