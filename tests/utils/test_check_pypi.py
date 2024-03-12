import sys

import pytest

from tests.platform_helper.conftest import UTILS_FIXTURES_DIR
from utils.check_pypi import check_for_version_in_pypi_releases
from utils.check_pypi import get_current_version
from utils.check_pypi import get_releases

TOML_UNSUPPORTED = (
    "tomllib added in 3.11. We don't anticipate needing to run this pipeline tool in older versions"
)


@pytest.mark.skipif(sys.version_info < (3, 11), reason=TOML_UNSUPPORTED)
def test_get_current_version__success():
    version = get_current_version(UTILS_FIXTURES_DIR / "pyproject.toml")
    assert version == "0.1.21"


@pytest.mark.skipif(sys.version_info < (3, 11), reason=TOML_UNSUPPORTED)
def test_get_current_version__fails_with_malformed_toml():
    from tomllib import TOMLDecodeError

    with pytest.raises(TOMLDecodeError):
        get_current_version(UTILS_FIXTURES_DIR / "pyproject_malformed.toml")


@pytest.mark.skipif(sys.version_info < (3, 11), reason=TOML_UNSUPPORTED)
def test_get_current_version__fails_with_missing_version():
    with pytest.raises(KeyError):
        get_current_version(UTILS_FIXTURES_DIR / "pyproject_no_version.toml")


def test_get_releases__success():
    releases = get_releases()
    assert "0.1.1" in releases
    assert "0.1.21" in releases


class FakeOpts:
    def __init__(self, **data):
        self.__dict__ = data


def test_check_for_version_in_pypi_releases__print_version_only(capsys):
    opts = FakeOpts(retry_interval=1, max_attempts=1, version=True)
    exit_code = check_for_version_in_pypi_releases(
        opts, "0.1.1", lambda: ["0.1.2", "0.1.21", "0.1.1"]
    )

    captured_output = capsys.readouterr()
    lines = [line.strip() for line in captured_output.out.split("\n") if line]

    assert exit_code == 0
    assert ["Version: 0.1.1"] == lines


def test_check_for_version_in_pypi_releases__version_found_immediately(capsys):
    opts = FakeOpts(retry_interval=1, max_attempts=3, version=False)
    exit_code = check_for_version_in_pypi_releases(
        opts, "0.1.1", lambda: ["0.1.2", "0.1.21", "0.1.1"]
    )

    captured_output = capsys.readouterr()
    lines = [line.strip() for line in captured_output.out.split("\n") if line]

    assert exit_code == 0
    assert ["Version: 0.1.1", "Attempt 1 of 3: Version 0.1.1 has been found in PyPI."] == lines


def test_check_for_version_in_pypi_releases__version_not_found(capsys):
    opts = FakeOpts(retry_interval=0.1, max_attempts=3, version=False)
    exit_code = check_for_version_in_pypi_releases(
        opts, "0.1.22", lambda: ["0.1.2", "0.1.21", "0.1.1"]
    )

    captured_output = capsys.readouterr()
    lines = [line.strip() for line in captured_output.out.split("\n") if line]

    assert exit_code == 1
    assert [
        "Version: 0.1.22",
        "Attempt 1 of 3: Package not yet found in PyPI. Retrying in 0.1s.",
        "Attempt 2 of 3: Package not yet found in PyPI. Retrying in 0.1s.",
        "Attempt 3 of 3: Version 0.1.22 could not be found in PyPI.",
    ] == lines


def test_check_for_version_in_pypi_releases__version_found_on_the_third_attempt(capsys):
    opts = FakeOpts(retry_interval=0.1, max_attempts=5, version=False)

    call_no = {"calls": 0}

    def releases_fn():
        call_no["calls"] += 1
        if call_no["calls"] <= 2:
            return ["0.1.2", "0.1.21", "0.1.1"]
        return ["0.1.2", "0.1.21", "0.1.22", "0.1.1"]

    exit_code = check_for_version_in_pypi_releases(opts, "0.1.22", releases_fn)

    captured_output = capsys.readouterr()
    lines = [line.strip() for line in captured_output.out.split("\n") if line]

    assert exit_code == 0
    assert [
        "Version: 0.1.22",
        "Attempt 1 of 5: Package not yet found in PyPI. Retrying in 0.1s.",
        "Attempt 2 of 5: Package not yet found in PyPI. Retrying in 0.1s.",
        "Attempt 3 of 5: Version 0.1.22 has been found in PyPI.",
    ] == lines
