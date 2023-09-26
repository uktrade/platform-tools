import os
from pathlib import Path
from shutil import copyfile
from shutil import rmtree

import pytest
from click.testing import CliRunner

from dbt_copilot_helper.commands.bootstrap import make_config
from dbt_copilot_helper.commands.check_cloudformation import (
    check_cloudformation as check_cloudformation_command,
)
from dbt_copilot_helper.commands.copilot import make_addons
from tests.conftest import BASE_DIR


def prepare_fake_cloudformation_templates(copilot_directory: Path, passing: bool) -> None:
    template = (
        "valid_cloudformation_template.yml" if passing else "invalid_cloudformation_template.yml"
    )
    addons_directory = Path(f"{BASE_DIR}/tests/test-application-deploy/copilot/environments/addons")
    addons_directory.mkdir(parents=True, exist_ok=True)
    copyfile(f"{BASE_DIR}/tests/fixtures/{template}", f"{addons_directory}/{template}")


def ensure_directory_does_not_exist(copilot_directory: Path) -> None:
    if copilot_directory.exists():
        rmtree(copilot_directory)
    assert not copilot_directory.exists(), "copilot directory should not exist"


@pytest.fixture
def copilot_directory() -> Path:
    return Path(f"{BASE_DIR}/tests/test-application-deploy/copilot")


@pytest.fixture
def test_application(copilot_directory):
    ensure_directory_does_not_exist(copilot_directory)
    os.chdir(copilot_directory.parent)
    CliRunner().invoke(make_config)
    CliRunner().invoke(make_addons)
    yield
    ensure_directory_does_not_exist(copilot_directory)


def test_check_cloudformation_with_no_args_summarises_all_successes(
    test_application, copilot_directory: Path
) -> None:
    prepare_fake_cloudformation_templates(copilot_directory, passing=True)

    result = CliRunner().invoke(
        check_cloudformation_command, args=["--directory", copilot_directory]
    )

    assert ">>> Running all checks" in result.output
    assert ">>> Running lint check" in result.output
    assert "The CloudFormation templates passed the following checks:\n  - lint" in result.output


def test_check_cloudformation_with_no_args_summarises_all_failures(
    test_application, copilot_directory: Path
) -> None:
    prepare_fake_cloudformation_templates(copilot_directory, passing=False)

    result = CliRunner().invoke(
        check_cloudformation_command, args=["--directory", copilot_directory]
    )

    assert (
        "The CloudFormation templates failed the following checks:\n  - lint [E0000 could not find expected ':'"
        in result.output
    )


def test_linting_check_passed(test_application, copilot_directory: Path) -> None:
    prepare_fake_cloudformation_templates(copilot_directory, passing=True)

    result = CliRunner().invoke(
        check_cloudformation_command, args=["lint", "--directory", copilot_directory]
    )

    assert result.exit_code == 0
    assert "The CloudFormation templates passed the following checks:\n  - lint" in result.output


def test_linting_check_failed(test_application, copilot_directory: Path) -> None:
    prepare_fake_cloudformation_templates(copilot_directory, passing=False)

    result = CliRunner().invoke(
        check_cloudformation_command, args=["lint", "--directory", copilot_directory]
    )

    assert result.exit_code != 0
    assert (
        "The CloudFormation templates failed the following checks:\n  - lint [E0000 could not find expected ':'"
        in result.output
    )
