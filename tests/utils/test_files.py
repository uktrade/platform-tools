import pytest
import yaml

from dbt_copilot_helper.utils.files import BOOTSTRAP_SCHEMA
from dbt_copilot_helper.utils.files import PIPELINES_SCHEMA
from dbt_copilot_helper.utils.files import load_and_validate_config
from dbt_copilot_helper.utils.files import mkfile
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


@pytest.mark.parametrize(
    "file_exists, overwrite, expected",
    [
        (False, False, "File test_file.txt created"),
        (False, True, "File test_file.txt created"),
        (True, True, "File test_file.txt overwritten"),
    ],
)
def test_mkfile_creates_or_overrides_the_file(tmp_path, file_exists, overwrite, expected):
    filename = "test_file.txt"
    file_path = tmp_path / filename
    if file_exists:
        file_path.touch()

    contents = "The content"

    message = mkfile(tmp_path, filename, contents, overwrite)

    assert file_path.exists()
    assert file_path.read_text() == contents
    assert message == expected


def test_mkfile_does_nothing_if_file_already_exists_but_override_is_false(tmp_path):
    filename = "test_file.txt"
    file_path = tmp_path / filename
    file_path.touch()

    message = mkfile(tmp_path, filename, contents="does not matter", overwrite=False)

    assert message == f"File {filename} exists; doing nothing"
