from pathlib import Path

import yaml
from yaml.parser import ParserError

from dbt_copilot_helper.utils.files import load_and_validate_config
from dbt_copilot_helper.utils.messages import abort_with_error
from dbt_copilot_helper.utils.validation import BOOTSTRAP_SCHEMA


def get_application_name():
    app_name = None

    try:
        app_config = load_and_validate_config("bootstrap.yml", BOOTSTRAP_SCHEMA)
        app_name = app_config["app"]
    except (FileNotFoundError, ParserError):
        pass

    try:
        if app_name is None:
            app_config = yaml.safe_load(Path("copilot/.workspace").read_text())
            app_name = app_config["application"]
    except (FileNotFoundError, ParserError):
        pass

    if app_name is None:
        abort_with_error("No valid bootstrap.yml or copilot/.workspace file found")

    return app_name
