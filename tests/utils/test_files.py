import yaml

from dbt_copilot_helper.utils.files import BOOTSTRAP_SCHEMA
from dbt_copilot_helper.utils.files import load_and_validate_config
from tests.conftest import FIXTURES_DIR


def test_load_and_validate_config_valid_file():
    """Test that, given the path to a valid yaml file, load_and_validate_config
    returns the loaded yaml unmodified."""

    path = FIXTURES_DIR / "valid_bootstrap_config.yml"
    validated = load_and_validate_config(path, BOOTSTRAP_SCHEMA)

    with open(path, "r") as fd:
        conf = yaml.safe_load(fd)

    assert validated == conf
