from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from commands.copilot_cli import WAF_ACL_ARN_KEY
from commands.copilot_cli import copilot as cli


class TestApplyWAF:
    def test_require_copilot_dir(self, fakefs):
        assert not Path("./copilot").is_dir()

        runner = CliRunner()

        result = runner.invoke(cli, ["apply-waf"])

        assert result.exit_code == 1
        assert (
            result.output
            == "Cannot find copilot directory. Run this command in the root of the deployment repository.\n"
        )

    def test_no_envs(self, fakefs):
        fakefs.create_dir("./copilot/environments")

        runner = CliRunner()

        result = runner.invoke(cli, ["apply-waf"])

        assert result.exit_code == 1
        assert result.output == "Cannot add WAF CFN templates: No environments found in ./copilot/environments/\n"

    @pytest.mark.parametrize(
        "arn",
        [
            f"{WAF_ACL_ARN_KEY}: None",
            f"{WAF_ACL_ARN_KEY}:",
            f"{WAF_ACL_ARN_KEY}: not-a-valid-arn",
            "",
        ],
    )
    def test_invalid_waf_arn(self, arn, fakefs):
        fakefs.create_file("./copilot/environments/staging/manifest.yml", contents=arn)

        runner = CliRunner()

        result = runner.invoke(cli, ["apply-waf"])

        assert result.exit_code == 1
        assert (
            result.output
            == "Cannot add WAF CFN templates: Set a valid `waf-acl-arn` in each ./copilot/environments/*/manifest.yml file\n"
        )

    def test_success(self, fakefs):
        fakefs.create_file(
            "./copilot/environments/development/manifest.yml",
            contents=f"{WAF_ACL_ARN_KEY}: arn:aws:wafv2:development-dummy-arn",
        )
        fakefs.create_file(
            "./copilot/environments/staging/manifest.yml",
            contents=f"{WAF_ACL_ARN_KEY}: arn:aws:wafv2:staging-dummy-arn",
        )
        fakefs.create_file(
            "./copilot/environments/production/manifest.yml",
            contents=f"{WAF_ACL_ARN_KEY}: arn:aws:wafv2:production-dummy-arn",
        )

        runner = CliRunner()

        result = runner.invoke(cli, ["apply-waf"])

        assert Path("./copilot/environments/addons/addons.parameters.yml").exists()
        with open(Path("./copilot/environments/addons/waf.yml"), "r") as fd:
            # tell yaml to ignore CFN ! function prefixes
            yaml.add_multi_constructor("!", lambda loader, suffix, node: None, Loader=yaml.SafeLoader)
            waf = yaml.safe_load(fd)

        assert set(waf["Mappings"]["EnvWAFConfigurationMap"].keys()) == {"development", "staging", "production"}

        for env_name, config in waf["Mappings"]["EnvWAFConfigurationMap"].items():
            assert config["WebACLArn"] == f"arn:aws:wafv2:{env_name}-dummy-arn"

        assert result.exit_code == 0
