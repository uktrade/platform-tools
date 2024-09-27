import yaml

from pathlib import Path

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE


def _read_config_file_contents():
    if Path(PLATFORM_CONFIG_FILE).exists():
        return Path(PLATFORM_CONFIG_FILE).read_text()


def load_unvalidated_config_file():
    file_contents = _read_config_file_contents()
    if not file_contents:
        return {}
    try:
        return yaml.safe_load(file_contents)
    except yaml.parser.ParserError:
        return {}


def get_environment_pipeline_names():
    pipelines_config = load_unvalidated_config_file().get("environment_pipelines")
    if pipelines_config:
        return pipelines_config.keys()
    return {}


def is_terraform_project() -> bool:
    config = yaml.safe_load(Path(PLATFORM_CONFIG_FILE).read_text())
    return not config.get("legacy_project", False)
