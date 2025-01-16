from dbt_platform_helper.providers.files import FileProvider


class TemplateProvider:
    def __init__(self, fileprovider=FileProvider()):
        self.fileprovider = fileprovider

    def generate_codebase_pipeline_config(self, codebase_pipeline_config):
        pass
