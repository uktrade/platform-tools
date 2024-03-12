import re
import subprocess


def git_remote():
    git_repo = subprocess.run(
        ["git", "remote", "get-url", "origin"], capture_output=True, text=True
    ).stdout.strip()

    if not git_repo:
        return

    _, repo = git_repo.split("@")[1].split(":")

    return re.sub(r".git$", "", repo)
