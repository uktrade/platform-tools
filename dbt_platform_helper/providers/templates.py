from pathlib import Path

from dbt_platform_helper.providers.files import FileProvider


class TemplateProvider:
    def __init__(self, file_provider: FileProvider = FileProvider()):
        self.file_provider = file_provider

    def generate_codebase_pipeline_config(self, codebase_pipeline_config: list[dict]):
        self.file_provider.mkfile(
            str(Path(".").absolute()), "terraform/codebase-pipelines", "", True
        )
