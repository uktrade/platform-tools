import pytest
import yaml

from dbt_copilot_helper.utils.files import BOOTSTRAP_SCHEMA
from dbt_copilot_helper.utils.files import PIPELINES_SCHEMA
from dbt_copilot_helper.utils.files import load_and_validate_config
from tests.conftest import FIXTURES_DIR


@pytest.mark.parametrize(
    "schema,yaml_file",
    [
        (BOOTSTRAP_SCHEMA, "valid_bootstrap_config.yml"),
        (PIPELINES_SCHEMA, "pipeline/pipelines.yml"),
    ],
)
def test_load_and_validate_config_valid_file(schema, yaml_file):
    """Test that, given the path to a valid yaml file, load_and_validate_config
    returns the loaded yaml unmodified."""

    path = FIXTURES_DIR / yaml_file
    validated = load_and_validate_config(path, schema)

    with open(path, "r") as fd:
        conf = yaml.safe_load(fd)

    assert validated == conf
