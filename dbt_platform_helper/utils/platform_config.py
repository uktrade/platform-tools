import yaml

from pathlib import Path

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE


def read_config_file():
    if Path(PLATFORM_CONFIG_FILE).exists():
        return Path(PLATFORM_CONFIG_FILE).read_text()


def load_config_file():
    file_contents = read_config_file()
    if not file_contents:
        return None
    try:
        return yaml.safe_load(file_contents)
    except yaml.parser.ParserError:
        return None


def get_environment_pipeline_names():
    config = load_config_file()

    try:
        return config.get("environment_pipelines", {}).keys()
    except AttributeError:
        return {}


def is_terraform_project() -> bool:
    config = yaml.safe_load(Path(PLATFORM_CONFIG_FILE).read_text())
    return not config.get("legacy_project", False)
