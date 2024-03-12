import argparse
import json
import time
from urllib.request import urlopen

PYPI_RELEASES_URL = "https://pypi.org/pypi/dbt-platform-tools/json"
OK = 0
FAIL = 1


def opts():
    parser = argparse.ArgumentParser(
        description="Tool to check PyPI for the presence of the platform-tools package"
    )
    parser.add_argument("--retry-interval", help="Delay before retrying", type=int, default=6)
    parser.add_argument("--max-attempts", help="Maximum number of attempts", type=int, default=1)
    parser.add_argument("--version", help="Display the project version", action="store_true")
    return parser.parse_args()


def check_for_version_in_pypi_releases(options, version, get_releases_fn):
    print("Version:", version)
    if options.version:
        return OK
    for i in range(options.max_attempts):
        print(f"Attempt {i + 1} of {options.max_attempts}: ", end="")
        releases = get_releases_fn()
        if version in releases:
            print(f"Version {version} has been found in PyPI.")
            return OK
        if i + 1 < options.max_attempts:
            print(f"Package not yet found in PyPI. Retrying in {options.retry_interval}s.")
        time.sleep(options.retry_interval)

    print(f"Version {version} could not be found in PyPI.")
    return FAIL


def get_releases():
    pypi_releases = urlopen(PYPI_RELEASES_URL)
    data = json.loads(pypi_releases.read())
    return data["releases"].keys()


def get_current_version(project_file):
    with open(project_file, "rb") as fh:
        import tomllib

        pyproject = tomllib.load(fh)
        version = pyproject["tool"]["poetry"]["version"]
        return version


if __name__ == "__main__":
    exit(
        check_for_version_in_pypi_releases(
            opts(), get_current_version("pyproject.toml"), get_releases
        )
    )
