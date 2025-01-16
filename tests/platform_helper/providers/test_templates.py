from unittest.mock import Mock

from dbt_platform_helper.providers.templates import TemplateProvider


def test_generate_codebase_pipeline_config_creates_file():
    file_provider = Mock()
    TemplateProvider(file_provider)
