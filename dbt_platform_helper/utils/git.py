import re
import subprocess


def git_remote():
    git_repo = subprocess.run(
        ["git", "remote", "get-url", "origin"], capture_output=True, text=True
    ).stdout.strip()

    if not git_repo:
        return

    # Temporary hacked in line from Ben's branch to enable work in this branch to continue
    repo = re.search(r"[^/:]*?/[^/]*?\.git\Z", git_repo).group()

    return re.sub(r".git$", "", repo)
