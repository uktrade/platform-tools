from pathlib import Path
from typing import Dict

import click
from prettytable import PrettyTable

from dbt_copilot_helper.exceptions import IncompatibleMajorVersion
from dbt_copilot_helper.exceptions import ValidationException
from dbt_copilot_helper.utils import versioning
from dbt_copilot_helper.utils.click import ClickDocOptGroup

yes = "\033[92m✔\033[0m"
no = "\033[91m✖\033[0m"
maybe = "\033[93m?\033[0m"

RECOMMENDATIONS = {
    "dbt-copilot-tools-upgrade": (
        "Upgrade dbt-copilot-tools to version {version} `pip install "
        "--upgrade dbt-copilot-tools=={version}`."
    ),
    "dbt-copilot-tools-upgrade-note": (
        "Post upgrade, run `copilot-helper copilot make-addons` to " "update your addon templates."
    ),
    "generic-tool-upgrade": "Upgrade {tool} to version {version}.",
}


@click.group(cls=ClickDocOptGroup)
def config():
    """Perform actions on configuration files."""


@config.command()
def validate():
    """Validate deployment or application configuration."""
    ran_checks = False
    if Path("copilot").exists():
        click.secho("\nDetected a deployment repository", fg="blue")
        deployment()
        ran_checks = True

    if not ran_checks:
        click.secho("Could not find a deployment repository, no checks to run.", fg="red")
        exit(1)


def deployment():
    click.secho()

    compatible = True

    tool_versions()
    click.secho("Checking addons templates versions...", fg="blue")

    app_version, app_released_version = versioning.get_app_versions()
    addons_templates_table = PrettyTable()
    addons_templates_table.field_names = [
        "Addons Template File",
        "Generated with",
        "Compatible with local?",
        "Compatible with latest?",
    ]
    addons_templates_table.align["Addons Template File"] = "l"

    addons_templates = list(Path("./copilot").glob("**/addons/*"))
    # Sort by template file path
    addons_templates.sort(key=lambda e: str(e))
    # Bring environment addons to the top
    addons_templates.sort(key=lambda e: "environments/" not in str(e))

    recommendations = {}

    if Path("storage.yml").exists():
        recommendations["storage.yml"] = (
            "The file `storage.yml` is incompatible with version "
            f"{versioning.string_version(app_released_version)} of "
            "dbt-copilot-tools, move contents to `addons.yml` and "
            "delete `storage.yml`."
        )

    for template_file in addons_templates:
        generated_with_version = maybe
        local_compatible_symbol = yes
        latest_compatible_symbol = yes

        try:
            generated_with_version = versioning.get_template_generated_with_version(
                str(template_file.resolve())
            )
            versioning.validate_template_version(app_version, str(template_file.resolve()))
        except IncompatibleMajorVersion:
            local_compatible_symbol = no
            compatible = False
            recommendations["dbt-copilot-tools-upgrade"] = RECOMMENDATIONS[
                "dbt-copilot-tools-upgrade"
            ].format(version=versioning.string_version(app_released_version))
            recommendations["dbt-copilot-tools-upgrade-note"] = RECOMMENDATIONS[
                "dbt-copilot-tools-upgrade-note"
            ]
        except ValidationException:
            local_compatible_symbol = maybe
            compatible = False
            recommendations["dbt-copilot-tools-upgrade"] = RECOMMENDATIONS[
                "dbt-copilot-tools-upgrade"
            ].format(version=versioning.string_version(app_released_version))
            recommendations["dbt-copilot-tools-upgrade-note"] = RECOMMENDATIONS[
                "dbt-copilot-tools-upgrade-note"
            ]

        try:
            generated_with_version = versioning.get_template_generated_with_version(
                str(template_file.resolve())
            )
            versioning.validate_template_version(app_released_version, str(template_file.resolve()))
        except IncompatibleMajorVersion:
            latest_compatible_symbol = no
            compatible = False
        except ValidationException:
            latest_compatible_symbol = maybe
            compatible = False

        addons_templates_table.add_row(
            [
                template_file.relative_to("."),
                maybe
                if latest_compatible_symbol is maybe
                else versioning.string_version(generated_with_version),
                local_compatible_symbol,
                latest_compatible_symbol,
            ]
        )

    click.secho(addons_templates_table)
    render_recommendations(recommendations)

    exit(0 if compatible else 1)


def tool_versions():
    click.secho("Checking tooling versions...", fg="blue")
    recommendations = {}

    copilot_version, copilot_released_version = versioning.get_copilot_versions()
    if copilot_version is None:
        recommendations[
            "install-copilot"
        ] = "Install AWS Copilot https://aws.github.io/copilot-cli/"

    aws_version, aws_released_version = versioning.get_aws_versions()
    if aws_version is None:
        recommendations["install-aws"] = "Install AWS CLI https://aws.amazon.com/cli/"

    app_version, app_released_version = versioning.get_app_versions()

    tool_versions_table = PrettyTable()
    tool_versions_table.field_names = [
        "Tool",
        "Local version",
        "Released version",
        "Running latest?",
    ]
    tool_versions_table.align["Tool"] = "l"

    tool_versions_table.add_row(
        [
            "aws",
            versioning.string_version(aws_version),
            versioning.string_version(aws_released_version),
            no if aws_version != aws_released_version else yes,
        ]
    )
    tool_versions_table.add_row(
        [
            "copilot",
            versioning.string_version(copilot_version),
            versioning.string_version(copilot_released_version),
            no if copilot_version != copilot_released_version else yes,
        ]
    )
    tool_versions_table.add_row(
        [
            "dbt-copilot-tools",
            versioning.string_version(app_version),
            versioning.string_version(app_released_version),
            no if app_version != app_released_version else yes,
        ]
    )

    click.secho(tool_versions_table)

    if aws_version != aws_released_version and "install-aws" not in recommendations:
        recommendations["aws-upgrade"] = RECOMMENDATIONS["generic-tool-upgrade"].format(
            tool="AWS CLI",
            version=versioning.string_version(aws_released_version),
        )

    if copilot_version != copilot_released_version and "install-copilot" not in recommendations:
        recommendations["copilot-upgrade"] = RECOMMENDATIONS["generic-tool-upgrade"].format(
            tool="AWS Copilot",
            version=versioning.string_version(copilot_released_version),
        )

    if app_version != app_released_version:
        recommendations["dbt-copilot-tools-upgrade"] = RECOMMENDATIONS[
            "dbt-copilot-tools-upgrade"
        ].format(version=versioning.string_version(app_released_version))
        recommendations["dbt-copilot-tools-upgrade-note"] = RECOMMENDATIONS[
            "dbt-copilot-tools-upgrade-note"
        ]

    render_recommendations(recommendations)


def render_recommendations(recommendations: Dict[str, str]):
    if recommendations:
        click.secho("\nRecommendations:\n", bold=True)

        for name, recommendation in recommendations.items():
            if name.endswith("-note"):
                continue
            click.secho(f"  - {recommendation}")
            if recommendations.get(f"{name}-note", False):
                click.secho(f"    {recommendations.get(f'{name}-note')}")

        click.secho()
