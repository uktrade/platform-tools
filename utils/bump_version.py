import subprocess
from pathlib import Path

import semver
import tomlkit

from utils.check_pypi import get_releases


def get_pyproject_version():
    root_dir = Path(__file__, "..").resolve().parent
    with open(root_dir / "pyproject.toml", "rb") as fh:
        project = tomlkit.load(fh)
        return project["tool"]["poetry"]["version"]


def _get_next_version(version, versions, bump_version):
    sorted_versions = sorted([semver.Version.parse(v) for v in versions])
    current_version = sorted_versions[-1]
    if semver.Version.parse(version) > current_version:
        return version
    if bump_version:
        return str(current_version.bump_patch())
    return str(current_version)


def bump_version_if_required(versions, bump_version):
    pyproject_version = get_pyproject_version()
    correct_version = _get_next_version(pyproject_version, versions, bump_version)

    if correct_version == pyproject_version:
        return 0

    root_dir = Path(__file__, "..").resolve().parent
    with open(root_dir / "pyproject.toml", "rb") as fh:
        project = tomlkit.load(fh)

    print(f"{'Bumping' if bump_version else 'Setting'} the project version to {correct_version}")
    project["tool"]["poetry"]["version"] = correct_version

    with open(root_dir / "pyproject.toml", "w") as fh:
        tomlkit.dump(project, fh)

    return 1


def _is_in(filepath: Path, directories: list[str]):
    for d in directories:
        try:
            filepath.relative_to(Path(d))
            return True
        except ValueError:
            # File is not in the directory
            pass


def version_should_be_bumped(files):
    for f in files:
        filepath = Path(f)
        if filepath.name == "README.md":
            continue
        if _is_in(filepath, ["dbt_copilot_helper", "utils"]):
            return True
        if str(filepath) in ["copilot_helper.py", "pyproject.toml", "poetry.lock"]:
            return True

    return False


def _get_changed_files():
    merge_base = subprocess.run(
        ["git", "merge-base", "HEAD", "main"], capture_output=True, text=True
    ).stdout.strip()
    changed_files = subprocess.run(
        ["git", "diff", "--name-only", merge_base], capture_output=True, text=True
    ).stdout.strip()

    return changed_files.split("\n")


if __name__ == "__main__":
    bump_required = version_should_be_bumped(_get_changed_files())
    exit(bump_version_if_required(get_releases(), bump_required))
