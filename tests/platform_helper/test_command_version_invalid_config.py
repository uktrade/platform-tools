import yaml

from pathlib import Path
from click.testing import CliRunner

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE


def test_works_with_incompatible_config_version_with_pipeline_override(
    fakefs,
    invalid_platform_config_with_platform_version_overrides,
):
    fakefs.create_file(
        Path(PLATFORM_CONFIG_FILE),
        contents=yaml.dump(invalid_platform_config_with_platform_version_overrides),

    )
    from dbt_platform_helper.commands.version import get_platform_helper_for_project
    result = CliRunner().invoke(get_platform_helper_for_project, ["--pipeline", "prod-main"])

    assert result.exit_code == 0
    assert result.output == '9.0.9\n'