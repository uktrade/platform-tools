from pathlib import Path
from unittest.mock import Mock

from dbt_platform_helper.providers.templates import TemplateProvider


def test_generate_codebase_pipeline_config_creates_file():
    codebase_pipeline_config = [
        {
            "name": "test",
            "repository": "uktrade/repo1",
            "services": [
                {"run_group_1": ["web"]},
                {"run_group_2": ["api", "celery-worker"]},
            ],
            "pipelines": [
                {"name": "main", "branch": "main", "environments": [{"name": "dev"}]},
                {
                    "name": "tagged",
                    "tag": True,
                    "environments": [{"name": "dev"}, {"name": "prod", "requires_approval": True}],
                },
            ],
        }
    ]

    file_provider = Mock()
    template_provider = TemplateProvider(file_provider)

    template_provider.generate_codebase_pipeline_config(codebase_pipeline_config)

    assert file_provider.mkfile.call_count == 1
    base_path, file_path, contents, overwrite = file_provider.mkfile.call_args.args
    assert base_path == str(Path(".").absolute())
    assert file_path == "terraform/codebase-pipelines"
    assert overwrite
