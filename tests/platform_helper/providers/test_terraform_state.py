import json
import subprocess
from unittest.mock import patch

from dbt_platform_helper.providers.terraform_state import pull_terraform_state

MOCK_STATE = {
    "version": 4,
    "terraform_version": "1.12.2",
    "serial": 76,
}


class TestPull:
    @patch("dbt_platform_helper.providers.terraform_state.subprocess.run", spec=True)
    def test_success(self, mock_subprocess_run, tmp_path):
        mock_subprocess_run.return_value = subprocess.CompletedProcess(
            args=["terraform", "state", "pull"],
            returncode=0,
            stdout=json.dumps(MOCK_STATE),
            stderr=None,
        )

        result = pull_terraform_state(tmp_path)

        assert result == MOCK_STATE
        mock_subprocess_run.assert_called_once_with(
            ["terraform", "state", "pull"],
            cwd=tmp_path,
            stdout=subprocess.PIPE,
            check=True,
        )
