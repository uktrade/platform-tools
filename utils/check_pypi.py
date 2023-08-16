import argparse
import time
import tomllib
import xml.etree.ElementTree as ET
from urllib.request import urlopen

PYPI_RELEASES_URL = "https://pypi.org/rss/project/dbt-copilot-tools/releases.xml"


def opts():
    parser = argparse.ArgumentParser(description="Tool to check PyPI for the presence of the copilot-tools package")
    parser.add_argument("--retry-delay", help="Delay before retrying", type=int, default=6)
    parser.add_argument("--max-retries", help="Maximum number of retries", type=int, default=20)
    return parser.parse_args()


def main():
    options = opts()
    version = get_current_version()
    for i in range(options.max_retries):
        print(f"Attempt {i + 1} of {options.max_retries}")
        if version in get_releases():
            print(f"Version {version} has been found in PyPI.")
            exit(0)
        print(f"Package not yet found in PyPI. Retrying in {options.retry_delay}s.")
        time.sleep(options.retry_delay)

    print(f"Version {version} could not be found in PyPI.")
    exit(1)


def get_releases():
    pypi_releases = urlopen(PYPI_RELEASES_URL)
    rss_feed = ET.fromstring(pypi_releases.read())
    channel = rss_feed.find("channel")
    items = channel.findall("item")
    return [item.find("title").text for item in items]


def get_current_version():
    with open("pyproject.toml", "rb") as fh:
        pyproject = tomllib.load(fh)
        version = pyproject["tool"]["poetry"]["version"]
        print("Version:", version)
        return version


if __name__ == "__main__":
    main()
