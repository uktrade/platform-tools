# TODO - "most" of this is now tested by the new test_command_environment, some of this should be delagated to domain-level tests instead.
# Needs reviewing and then the file should be deleted.

from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from dbt_platform_helper.commands.environment import generate_terraform
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from tests.platform_helper.conftest import BASE_DIR


class TestGenerate:

    @patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    @patch("dbt_platform_helper.domain.copilot_environment.get_aws_session_or_abort")
    @pytest.mark.parametrize(
        "env_modules_version, cli_modules_version, expected_version, should_include_moved_block",
        [
            (None, None, "5", True),
            ("7", None, "7", True),
            (None, "8", "8", True),
            ("9", "10", "10", True),
            ("9-tf", "10", "10", True),
        ],
    )
    # Test covers different versioning scenarios, ensuring cli correctly overrides config version
    def test_generate_terraform(
        self,
        mock_get_aws_session_1,
        fakefs,
        env_modules_version,
        cli_modules_version,
        expected_version,
        should_include_moved_block,
    ):

        environment_config = {
            "*": {
                "vpc": "vpc3",
                "accounts": {
                    "deploy": {"name": "non-prod-acc", "id": "1122334455"},
                    "dns": {"name": "non-prod-dns-acc", "id": "6677889900"},
                },
            },
            "test": None,
        }

        # This block is relevant for ensuring the moved block test gets output and
        # for testing that the correct version of terraform is in the generated file
        # TODO can be tested at domain level, testing generated content directly rather
        # than the file
        if env_modules_version:
            environment_config["test"] = {
                "versions": {"terraform-platform-modules": env_modules_version}
            }

        mocked_session = MagicMock()
        mock_get_aws_session_1.return_value = mocked_session

        # TODO Why copilot here?
        fakefs.add_real_directory(
            BASE_DIR / "tests" / "platform_helper", read_only=False, target_path="copilot"
        )
        fakefs.create_file(
            PLATFORM_CONFIG_FILE,
            contents=yaml.dump({"application": "my-app", "environments": environment_config}),
        )

        args = ["--name", "test"]

        # Tests that command works with --terraform-platform-modules-version flag
        if cli_modules_version:
            args.extend(["--terraform-platform-modules-version", cli_modules_version])

        result = CliRunner().invoke(generate_terraform, args)

        assert "File terraform/environments/test/main.tf created" in result.output
        main_tf = Path("terraform/environments/test/main.tf")
        assert main_tf.exists()
        content = main_tf.read_text()

        assert "# WARNING: This is an autogenerated file, not for manual editing." in content
        assert (
            f"git::https://github.com/uktrade/terraform-platform-modules.git//extensions?depth=1&ref={expected_version}"
            in content
        )
        moved_block = "moved {\n  from = module.extensions-tf\n  to   = module.extensions\n}\n"
        assert moved_block in content
