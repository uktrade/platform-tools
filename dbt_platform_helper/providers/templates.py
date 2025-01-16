from pathlib import Path

from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.utils.template import setup_templates


class TemplateProvider:
    def __init__(self, file_provider: FileProvider = FileProvider()):
        self.file_provider = file_provider

    def generate_codebase_pipeline_config(self, codebase_pipeline_config: list[dict]):
        codebase_pipeline_template = setup_templates().get_template("codebase-pipelines/main.tf")
        contents = codebase_pipeline_template.render({})
        self.file_provider.mkfile(
            str(Path(".").absolute()), "terraform/codebase-pipelines", contents, True
        )
