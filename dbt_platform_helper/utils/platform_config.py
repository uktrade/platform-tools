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


def is_s3_bucket_data_migration_enabled(bucket_name):
    config = yaml.safe_load(Path(PLATFORM_CONFIG_FILE).read_text())
    extensions = config.get("extensions", {})

    for extension_name, extension_data in extensions.items():
        if extension_data.get("type") == "s3":
            environments = extension_data.get("environments", {})

            for env_name, env_data in environments.items():
                if env_data.get("bucket_name") == bucket_name:
                    return env_data.get("data_migration") is not None

    return False