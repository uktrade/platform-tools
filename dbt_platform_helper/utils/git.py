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

    if repository_url.startswith("https"):
        repo = repository_url.split("//")[1].split("/", maxsplit=1)[1]
    else:
        repo = repository_url.split(":")[1]

    return re.sub(r".git$", "", repo)
