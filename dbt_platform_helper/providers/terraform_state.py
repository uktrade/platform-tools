import json
import subprocess

from dbt_platform_helper.platform_exception import PlatformException


def pull_terraform_state(config_dir):
    try:
        result = subprocess.run(
            ["terraform", "state", "pull"],
            cwd=config_dir,
            stdout=subprocess.PIPE,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise PlatformException(f"Failed to pull a copy of the terraform state: {e}") from e
    return json.loads(result.stdout)
