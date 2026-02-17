import json
import subprocess

from dbt_platform_helper.platform_exception import PlatformException


class TerraformProvider:
    def init(self, config_dir):
        try:
            subprocess.run(
                ["terraform", "init"],
                cwd=config_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding="utf-8",
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise PlatformException(
                f"Failed to init terraform: subprocess exited with status {e.returncode}. Subprocess output:\n{e.output}"
            ) from e

    def pull_state(self, config_dir):
        try:
            result = subprocess.run(
                ["terraform", "state", "pull"],
                cwd=config_dir,
                stdout=subprocess.PIPE,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise PlatformException(f"Failed to pull a copy of the terraform state: {e}") from e
        if result.stdout:
            return json.loads(result.stdout)
        else:
            # If the given terraform config has never been applied (and thus the state file doesn't
            # yet exist), `terraform state pull` exits 0 with empty output. We should ensure we
            # handle this case. I think the sensible thing to do is to successfully return an
            # empty dict.
            return {}
