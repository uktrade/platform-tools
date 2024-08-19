from pathlib import Path

import yaml

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.utils.validation import load_and_validate_platform_config


def get_environment_pipeline_names():
    if not Path(PLATFORM_CONFIG_FILE).exists():
        return {}

    config = load_and_validate_platform_config(disable_aws_validation=True, disable_file_check=True)
    return config.get("environment_pipelines", {}).keys()


def is_terraform_project() -> bool:
    config = yaml.safe_load(Path(PLATFORM_CONFIG_FILE).read_text())
    return not config.get("legacy_project", False)
