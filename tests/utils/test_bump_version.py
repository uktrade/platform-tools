import pytest

from tests.copilot_helper.conftest import BASE_DIR
from utils.bump_version import bump_version_if_required
from utils.bump_version import get_next_version
from utils.bump_version import get_pyproject_version

PYPROJECT_CONTENT = """
[tool.poetry]
name = "dbt-copilot-tools"
version = "1.2.3"
"""


def test_get_pyproject_version(fs):
    fs.create_file(f"{BASE_DIR}/pyproject.toml", contents=PYPROJECT_CONTENT)
    version = get_pyproject_version()

    assert version == "1.2.3"


@pytest.mark.parametrize(
    "versions, expected",
    [
        (["1.1.1", "1.1.3"], "1.2.3"),
        (["1.1.1", "1.1.3", "1.2.2"], "1.2.3"),
        (["1.1.1", "1.1.3", "1.2.3"], "1.2.4"),
        (["1.1.1", "1.2.3", "1.2.4"], "1.2.5"),
    ],
)
def test_get_next_version(versions, expected):
    assert get_next_version("1.2.3", versions) == expected


@pytest.mark.parametrize(
    "versions, expected_version,expected_return_code",
    [
        (["1.1.1", "1.1.3"], "1.2.3", 0),
        (["1.1.1", "1.1.3", "1.2.2"], "1.2.3", 0),
        (["1.1.1", "1.1.3", "1.2.3"], "1.2.4", 1),
        (["1.1.1", "1.2.3", "1.2.4"], "1.2.5", 1),
    ],
)
def test_bump_version_if_required(versions, expected_version, expected_return_code, fs):
    fs.create_file(f"{BASE_DIR}/pyproject.toml", contents=PYPROJECT_CONTENT)

    return_code = bump_version_if_required(versions)

    assert return_code == expected_return_code
    assert get_pyproject_version() == expected_version
