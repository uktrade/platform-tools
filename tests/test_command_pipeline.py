import os
import shutil

from click.testing import CliRunner

from dbt_copilot_helper.commands.pipeline import generate
from tests.conftest import FIXTURES_DIR


def test_pipeline_generate_with_no_args_creates_the_pipeline_configuration(tmp_path):
    """"""

    os.chdir(tmp_path)
    shutil.copy(FIXTURES_DIR / "pipeline/pipelines.yml", "pipelines.yml")

    CliRunner().invoke(generate)

    # exp_files_dir = Path(EXPECTED_FILES_DIR) / "pipeline" / "pipelines" / "my-app-environments"
    # exp_manifest = exp_files_dir / "manifest.yml"
    # exp_buildspec = exp_files_dir / "buildspec.yml"
    # exp_cfn_patches = exp_files_dir / "overrides" / "cfn.patches.yml"
    output_dir = tmp_path / "copilot" / "pipelines" / "my-app-environments"

    assert (output_dir / "buildspec.yml").exists()
    assert (output_dir / "manifest.yml").exists()
    assert (output_dir / "overrides" / "cfn.patches.yml").exists()
