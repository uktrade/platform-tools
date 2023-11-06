from pathlib import Path
from unittest.mock import patch

from dbt_copilot_helper.utils.application import get_application_name


def test_getting_an_application_name_from_bootstrap(fakefs):
    fakefs.add_real_file(
        Path(__file__).parent.parent.joinpath("fixtures/valid_bootstrap_config.yml"),
        True,
        "bootstrap.yml",
    )
    assert get_application_name() == "test-app"


def test_getting_an_application_name_from_workspace(fakefs):
    fakefs.add_real_file(
        Path(__file__).parent.parent.joinpath("fixtures/valid_workspace.yml"),
        True,
        "copilot/.workspace",
    )
    assert get_application_name() == "test-app"


@patch("dbt_copilot_helper.utils.application.abort_with_error", return_value=None)
def test_getting_an_application_name_when_no_workspace_or_bootstrap(abort_with_error, fakefs):
    get_application_name()
    abort_with_error.assert_called_with("No valid bootstrap.yml or copilot/.workspace file found")
