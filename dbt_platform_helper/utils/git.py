import re
import subprocess


def git_remote():
    git_repo = subprocess.run(
        ["git", "remote", "get-url", "origin"], capture_output=True, text=True
    ).stdout.strip()
    return extract_repository_name(git_repo)


def extract_repository_name(repository_url):
    if not repository_url:
        return

    repo = re.search(r"[^/:]*?/[^/]*?\.git\Z", repository_url).group()

    return re.sub(r".git$", "", repo)
