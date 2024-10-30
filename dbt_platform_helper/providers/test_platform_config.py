from pathlib import Path

import yaml

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE


class PlatformConfigProvider:
    def __init__(self, platform_config_file=None):
        self.platform_config_file = (
            platform_config_file if platform_config_file else PLATFORM_CONFIG_FILE
        )

    def _read_config_file_contents(self):
        if Path(self.platform_config_file).exists():
            return Path(self.platform_config_file).read_text()

    def load_unvalidated_config_file(self):
        file_contents = self._read_config_file_contents()
        if not file_contents:
            return {}
        try:
            return yaml.safe_load(file_contents)
        except yaml.parser.ParserError:
            return {}

    # def get_environment_pipeline_names():
    #     pipelines_config = load_unvalidated_config_file().get("environment_pipelines")
    #     if pipelines_config:
    #         return pipelines_config.keys()
    #     return {}

    # def is_terraform_project() -> bool:
    #     config = yaml.safe_load(Path(PLATFORM_CONFIG_FILE).read_text())
    #     return not config.get("legacy_project", False)


def test_platform_config_provider_reads_config_from_default_file(fs):
    fs.create_file("platform-config.yml", contents=yaml.dump({"application": "test-squiggly-app"}))
    platform_config_provider = PlatformConfigProvider()
    config = platform_config_provider.load_unvalidated_config_file()
    assert config["application"] == "test-squiggly-app"


def test_platform_config_provider_reads_config_from_custom_config_file(fs):
    fs.create_file(
        "platform-config-2.yml", contents=yaml.dump({"application": "test-squiggly-app"})
    )
    platform_config_provider = PlatformConfigProvider("platform-config-2.yml")
    config = platform_config_provider.load_unvalidated_config_file()
    assert config["application"] == "test-squiggly-app"
