import json
import subprocess
from unittest.mock import patch

import pytest

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.terraform import TerraformProvider

MOCK_STATE = {
    "version": 4,
    "terraform_version": "1.12.2",
    "serial": 76,
}


class TestInit:
    @patch("dbt_platform_helper.providers.terraform.subprocess.run", spec=True)
    def test_success(self, mock_subprocess_run, tmp_path):
        mock_subprocess_run.return_value = subprocess.CompletedProcess(
            args=["terraform", "init"],
            returncode=0,
            stdout="terraform init logs\n",
            stderr=None,
        )

        provider = TerraformProvider()

        provider.init(tmp_path)

        mock_subprocess_run.assert_called_once_with(
            ["terraform", "init"],
            cwd=tmp_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            check=True,
        )

    @patch("dbt_platform_helper.providers.terraform.subprocess.run", spec=True)
    def test_platform_exception_raised_if_subprocess_exits_nonzero(
        self, mock_subprocess_run, tmp_path
    ):
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["terraform", "init"],
            output="terraform init logs\n",
            stderr=None,
        )

        provider = TerraformProvider()

        with pytest.raises(PlatformException) as e:
            provider.init(tmp_path)

        assert (
            str(e.value)
            == "Failed to init terraform: subprocess exited with status 1. Subprocess output:\nterraform init logs\n"
        )


class TestPullState:
    @patch("dbt_platform_helper.providers.terraform.subprocess.run", spec=True)
    def test_success(self, mock_subprocess_run, tmp_path):
        mock_subprocess_run.return_value = subprocess.CompletedProcess(
            args=["terraform", "state", "pull"],
            returncode=0,
            stdout=json.dumps(MOCK_STATE),
            stderr=None,
        )

        provider = TerraformProvider()

        result = provider.pull_state(tmp_path)

        assert result == MOCK_STATE
        mock_subprocess_run.assert_called_once_with(
            ["terraform", "state", "pull"],
            cwd=tmp_path,
            stdout=subprocess.PIPE,
            check=True,
        )

    @patch("dbt_platform_helper.providers.terraform.subprocess.run", spec=True)
    def test_platform_exception_raised_if_subprocess_exits_nonzero(
        self, mock_subprocess_run, tmp_path
    ):
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["terraform", "state", "pull"],
            output=b"",
            stderr=None,
        )

        provider = TerraformProvider()

        with pytest.raises(PlatformException) as e:
            provider.pull_state(tmp_path)

        assert "Failed to pull a copy of the terraform state" in str(e.value)
