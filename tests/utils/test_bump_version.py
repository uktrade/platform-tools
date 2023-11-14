import pytest
import semver

from tests.copilot_helper.conftest import BASE_DIR
from utils.bump_version import bump_version_if_required
from utils.bump_version import get_pyproject_version
from utils.bump_version import version_should_be_bumped

PYPROJECT_CONTENT = """
[tool.poetry]
name = "dbt-copilot-tools"
version = "%s"
"""


def test_get_pyproject_version(fs):
    fs.create_file(f"{BASE_DIR}/pyproject.toml", contents=PYPROJECT_CONTENT % "1.2.3")
    version = get_pyproject_version()

    assert version == "1.2.3"


@pytest.mark.parametrize(
    "version, bump_version, expected_version,expected_return_code",
    [
        ("1.2.3", True, "1.2.5", 1),
        ("1.2.3", False, "1.2.4", 1),
        ("1.2.4", True, "1.2.5", 1),
        ("1.2.4", False, "1.2.4", 0),
        ("1.3.0", True, "1.3.0", 0),
        ("1.3.0", False, "1.3.0", 0),
    ],
)
def test_bump_version_if_required(
    version, bump_version, expected_version, expected_return_code, fs, capsys
):
    versions = ["1.1.1", "1.1.2", "1.2.3", "1.2.4"]
    fs.create_file(f"{BASE_DIR}/pyproject.toml", contents=PYPROJECT_CONTENT % version)

    return_code = bump_version_if_required(versions, bump_version)

    assert return_code == expected_return_code
    assert get_pyproject_version() == semver.Version.parse(expected_version)

    out = capsys.readouterr().out
    if return_code == 0:
        assert "" == out
    else:
        assert f"project version to {expected_version}" in out
        assert out.startswith("Bumping" if bump_version else "Setting")


@pytest.mark.parametrize(
    "files, bump_expected",
    [
        ([], False),
        (["dbt_copilot_helper/utils/aws.py"], True),
        (["dbt_copilot_helper/templates/env/manifest.yml"], True),
        (["dbt_copilot_helper/README.md"], False),
        (["README.md"], False),
        (["pyproject.toml"], True),
        (["tests/utils/test_check_pypi.py"], False),
        (
            [
                "dbt_copilot_helper/utils/aws.py",
                "dbt_copilot_helper/templates/env/manifest.yml",
                "dbt_copilot_helper/README.md",
                "tests/utils/test_check_pypi.py",
            ],
            True,
        ),
    ],
)
def test_version_should_be_bumped(files, bump_expected):
    assert version_should_be_bumped(files) == bump_expected
