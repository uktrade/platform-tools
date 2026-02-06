import json
import subprocess
from unittest.mock import patch

import pytest

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.terraform import TerraformStateProvider

MOCK_STATE = {
    "version": 4,
    "terraform_version": "1.12.2",
    "serial": 76,
}


class TestPull:
    @patch("dbt_platform_helper.providers.terraform.subprocess.run", spec=True)
    def test_success(self, mock_subprocess_run, tmp_path):
        mock_subprocess_run.return_value = subprocess.CompletedProcess(
            args=["terraform", "state", "pull"],
            returncode=0,
            stdout=json.dumps(MOCK_STATE),
            stderr=None,
        )

        result = TerraformStateProvider().pull(tmp_path)

        assert result == MOCK_STATE
        mock_subprocess_run.assert_called_once_with(
            ["terraform", "state", "pull"],
            cwd=tmp_path,
            stdout=subprocess.PIPE,
            check=True,
        )

    @patch("dbt_platform_helper.providers.terraform.subprocess.run", spec=True)
    def test_subprocess_exits_nonzero(self, mock_subprocess_run, tmp_path):
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["terraform", "state", "pull"],
            output=b"",
            stderr=None,
        )

        with pytest.raises(PlatformException) as e:
            TerraformStateProvider().pull(tmp_path)

        assert "Failed to pull a copy of the terraform state" in str(e.value)
