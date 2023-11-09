from pathlib import Path

import semver
import tomlkit


def get_pyproject_version():
    root_dir = Path(__file__, "..").resolve().parent
    with open(root_dir / "pyproject.toml", "rb") as fh:
        project = tomlkit.load(fh)
        return project["tool"]["poetry"]["version"]


def get_next_version(version, versions):
    sorted_versions = sorted([semver.Version.parse(v) for v in versions])
    current_version = sorted_versions[-1]
    if semver.Version.parse(version) > current_version:
        return version
    return str(current_version.bump_patch())


def bump_version_if_required(versions):
    pyproject_version = get_pyproject_version()
    correct_version = get_next_version(pyproject_version, versions)

    if correct_version == pyproject_version:
        return 0

    root_dir = Path(__file__, "..").resolve().parent
    with open(root_dir / "pyproject.toml", "rb") as fh:
        project = tomlkit.load(fh)

    project["tool"]["poetry"]["version"] = correct_version

    with open(root_dir / "pyproject.toml", "w") as fh:
        tomlkit.dump(project, fh)

    return 1


if __name__ == "__main__":
    pass
    # exit(bump_version_if_required(get_releases()))
