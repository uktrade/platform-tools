import json
import subprocess


def pull_terraform_state(config_dir):
    result = subprocess.run(
        ["terraform", "state", "pull"],
        cwd=config_dir,
        stdout=subprocess.PIPE,
        check=True,
    )
    return json.loads(result.stdout)
