import os
import re
import subprocess
from importlib.metadata import version
from pathlib import Path
from typing import Tuple
from typing import Union

import click
import requests

from dbt_platform_helper.exceptions import IncompatibleMajorVersion
from dbt_platform_helper.exceptions import IncompatibleMinorVersion
from dbt_platform_helper.exceptions import ValidationException
from dbt_platform_helper.utils.files import mkfile


def string_version(input_version: Union[Tuple[int, int, int], None]) -> str:
    if input_version is None:
        return "unknown"
    major, minor, patch = input_version
    return ".".join([str(s) for s in [major, minor, patch]])


def parse_version(input_version: Union[str, None]) -> Union[Tuple[int, int, int], None]:
    if input_version is None:
        return None

    version_plain = input_version.replace("v", "")
    version_segments = re.split(r"[.\-]", version_plain)

    if len(version_segments) != 3:
        return None

    output_version = [0, 0, 0]
    for index, segment in enumerate(version_segments):
        try:
            output_version[index] = int(segment)
        except ValueError:
            output_version[index] = -1
    return output_version[0], output_version[1], output_version[2]


def get_copilot_versions() -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    copilot_version = None

    try:
        response = subprocess.run("copilot --version", capture_output=True, shell=True)
        [copilot_version] = re.findall(r"[0-9.]+", response.stdout.decode("utf8"))
    except ValueError:
        pass

    return parse_version(copilot_version), get_github_released_version("aws/copilot-cli")


def get_aws_versions() -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    aws_version = None
    try:
        response = subprocess.run("aws --version", capture_output=True, shell=True)
        matched = re.match(r"aws-cli/([0-9.]+)", response.stdout.decode("utf8"))
        aws_version = parse_version(matched.group(1))
    except ValueError:
        pass

    return aws_version, get_github_released_version("aws/aws-cli", True)


def get_github_released_version(repository: str, tags: bool = False) -> Tuple[int, int, int]:
    if tags:
        tags_list = requests.get(f"https://api.github.com/repos/{repository}/tags").json()
        versions = [parse_version(v["name"]) for v in tags_list]
        versions.sort(reverse=True)
        return versions[0]

    package_info = requests.get(f"https://api.github.com/repos/{repository}/releases/latest").json()
    return parse_version(package_info["tag_name"])


def get_app_versions():
    package_info = requests.get("https://pypi.org/pypi/dbt-platform-helper/json").json()
    released_versions = package_info["releases"].keys()
    parsed_released_versions = [parse_version(v) for v in released_versions]
    parsed_released_versions.sort(reverse=True)

    return parse_version(version("dbt-platform-helper")), parsed_released_versions[0]


def get_file_app_versions():
    version_from_file = Path(".platform-helper-version").read_text()
    return parse_version(version("dbt-platform-helper")), parse_version(version_from_file)


def validate_version_compatibility(
    app_version: Tuple[int, int, int], check_version: Tuple[int, int, int]
):
    app_major, app_minor, app_patch = app_version
    check_major, check_minor, check_patch = check_version
    app_version_as_string = string_version(app_version)
    check_version_as_string = string_version(check_version)

    if (app_major == 0 and check_major == 0) and (
        app_minor != check_minor or app_patch != check_patch
    ):
        raise IncompatibleMajorVersion(app_version_as_string, check_version_as_string)

    if app_major != check_major:
        raise IncompatibleMajorVersion(app_version_as_string, check_version_as_string)

    if app_minor != check_minor:
        raise IncompatibleMinorVersion(app_version_as_string, check_version_as_string)


def check_version_on_file_compatibility(
    app_version: Tuple[int, int, int], file_version: Tuple[int, int, int]
):
    app_major, app_minor, app_patch = app_version
    file_major, file_minor, file_patch = file_version

    return app_major == file_major and app_minor == file_minor and app_patch == file_patch


def get_template_generated_with_version(template_file_path: str) -> Tuple[int, int, int]:
    try:
        template_contents = Path(template_file_path).read_text()
        template_version = re.match(
            r"# Generated by platform-helper ([v.\-0-9]+)", template_contents
        ).group(1)
        return parse_version(template_version)
    except (IndexError, AttributeError):
        raise ValidationException(f"Template {template_file_path} has no version information")


def validate_template_version(app_version: Tuple[int, int, int], template_file_path: str):
    validate_version_compatibility(
        app_version,
        get_template_generated_with_version(template_file_path),
    )


def validate_platform_helper_file_version(template_file_path: str):
    validate_version_compatibility(
        get_file_app_versions()[1],
        get_template_generated_with_version(template_file_path),
    )


def generate_platform_helper_version_file(directory="."):
    base_path = Path(directory)
    copilot_version = string_version(get_app_versions()[0])
    click.echo(mkfile(base_path, ".platform-helper-version", f"{copilot_version}"))


def check_platform_helper_version_needs_update():
    if not running_as_installed_package() or "PLATFORM_TOOLS_SKIP_VERSION_CHECK" in os.environ:
        return

    app_version, app_released_version = get_app_versions()
    message = (
        f"You are running platform-helper v{string_version(app_version)}, upgrade to "
        f"v{string_version(app_released_version)} by running run `pip install "
        "--upgrade dbt-platform-helper`."
    )
    try:
        validate_version_compatibility(app_version, app_released_version)
    except IncompatibleMajorVersion:
        click.secho(message, fg="red")
    except IncompatibleMinorVersion:
        click.secho(message, fg="yellow")


def check_platform_helper_version_mismatch():
    if not running_as_installed_package():
        return

    app_version, on_file_version = get_file_app_versions()

    if not check_version_on_file_compatibility(app_version, on_file_version):
        message = (
            f"WARNING: You are running platform-helper v{string_version(app_version)} against "
            f"v{string_version(on_file_version)} specified by .platform-helper-version."
        )
        click.secho(message, fg="red")


def running_as_installed_package():
    return "site-packages" in __file__
