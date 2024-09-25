import yaml

from pathlib import Path

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE


def read_config_file():
    return Path(PLATFORM_CONFIG_FILE).read_text()


def load_config_file():
    try:
        return yaml.safe_load(read_config_file())
    except yaml.parser.ParserError:
        return None


def get_environment_pipeline_names():
    if not Path(PLATFORM_CONFIG_FILE).exists():
        return {}

    config = load_config_file()

    try:
        return config.get("environment_pipelines", {}).keys()
    except AttributeError:
        return {}


def is_terraform_project() -> bool:
    config = yaml.safe_load(Path(PLATFORM_CONFIG_FILE).read_text())
    return not config.get("legacy_project", False)
