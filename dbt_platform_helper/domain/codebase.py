import stat
import subprocess
from collections.abc import Callable
from pathlib import Path

import click
import requests
import yaml

from dbt_platform_helper.utils.files import mkfile
from dbt_platform_helper.utils.template import setup_templates


class Codebase:
    def __init__(
        self,
        input_fn: Callable[[str], str] = click.prompt,
        echo_fn: Callable[[str], str] = click.secho,
    ):
        self.input_fn = input_fn
        self.echo_fn = echo_fn

    def prepare():
        """Sets up an application codebase for use within a DBT platform
        project."""
        templates = setup_templates()

        repository = (
            subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True)
            .stdout.split("/")[-1]
            .strip()
            .removesuffix(".git")
        )

        if repository.endswith("-deploy") or Path("./copilot").exists():
            click.secho(
                "You are in the deploy repository; make sure you are in the application codebase repository.",
                fg="red",
            )
            exit(1)

        builder_configuration_url = "https://raw.githubusercontent.com/uktrade/ci-image-builder/main/image_builder/configuration/builder_configuration.yml"
        builder_configuration_response = requests.get(builder_configuration_url)
        builder_configuration_content = yaml.safe_load(
            builder_configuration_response.content.decode("utf-8")
        )
        builder_versions = next(
            (
                item
                for item in builder_configuration_content["builders"]
                if item["name"] == "paketobuildpacks/builder-jammy-base"
            ),
            None,
        )
        builder_version = max(x["version"] for x in builder_versions["versions"])
        # Temporary hack until https://uktrade.atlassian.net/browse/DBTP-351 is done
        # Will need a change in tests/platform_helper/expected_files/.copilot/config.yml, when removed.
        builder_version = min(builder_version, "0.4.240")

        Path("./.copilot/phases").mkdir(parents=True, exist_ok=True)
        image_build_run_contents = templates.get_template(f".copilot/image_build_run.sh").render()

        config_contents = templates.get_template(f".copilot/config.yml").render(
            repository=repository, builder_version=builder_version
        )

        click.echo(
            mkfile(
                Path("."), ".copilot/image_build_run.sh", image_build_run_contents, overwrite=True
            )
        )

        image_build_run_file = Path(".copilot/image_build_run.sh")
        image_build_run_file.chmod(image_build_run_file.stat().st_mode | stat.S_IEXEC)

        click.echo(mkfile(Path("."), ".copilot/config.yml", config_contents, overwrite=True))

        for phase in ["build", "install", "post_build", "pre_build"]:
            phase_contents = templates.get_template(f".copilot/phases/{phase}.sh").render()

            click.echo(
                mkfile(Path("./.copilot"), f"phases/{phase}.sh", phase_contents, overwrite=True)
            )
