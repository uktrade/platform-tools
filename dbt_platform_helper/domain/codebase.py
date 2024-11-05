import os
import stat
import subprocess
from collections.abc import Callable
from pathlib import Path

import click
import requests
import yaml
from boto3 import Session

from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import ApplicationNotFoundError
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.files import mkfile
from dbt_platform_helper.utils.template import setup_templates


class Codebase:
    def __init__(
        self,
        input_fn: Callable[[str], str] = click.prompt,
        echo_fn: Callable[[str], str] = click.secho,
        load_application_fn: Callable[[str], Application] = load_application,
        get_aws_session_or_abort_fn: Callable[[str], Application] = get_aws_session_or_abort,
    ):
        self.input_fn = input_fn
        self.echo_fn = echo_fn
        self.load_application_fn = load_application_fn
        self.get_aws_session_or_abort_fn = get_aws_session_or_abort_fn


    def prepare(self):
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

    def build(self, app: str, codebase: str, commit: str):
        """Trigger a CodePipeline pipeline based build."""
        session = self.get_aws_session_or_abort_fn()
        self.load_application_or_abort(session, app)

        check_if_commit_exists = subprocess.run(
            ["git", "branch", "-r", "--contains", f"{commit}"], capture_output=True, text=True
        )

        if check_if_commit_exists.stderr:
            self.echo_fn(
                f'The commit hash "{commit}" either does not exist or you need to run `git fetch`.',
                fg="red",
            )
            raise SystemExit(1)

        codebuild_client = session.client("codebuild")
        build_url = self.start_build_with_confirmation(
            codebuild_client,
            f'You are about to build "{app}" for "{codebase}" with commit "{commit}". Do you want to continue?',
            {
                "projectName": f"codebuild-{app}-{codebase}",
                "artifactsOverride": {"type": "NO_ARTIFACTS"},
                "sourceVersion": commit,
            },
        )

        if build_url:
            return self.echo_fn(
                f"Your build has been triggered. Check your build progress in the AWS Console: {build_url}"
            )

        return self.echo_fn("Your build was not triggered.")

    def get_build_url_from_arn(self, build_arn: str) -> str:
        _, _, _, region, account_id, project_name, build_id = build_arn.split(":")
        project_name = project_name.removeprefix("build/")
        return (
            f"https://eu-west-2.console.aws.amazon.com/codesuite/codebuild/{account_id}/projects/"
            f"{project_name}/build/{project_name}%3A{build_id}"
        )

    def start_build_with_confirmation(self, codebuild_client, confirmation_message, build_options):
        if click.confirm(confirmation_message):
            response = codebuild_client.start_build(**build_options)
            return self.get_build_url_from_arn(response["build"]["arn"])

    def load_application_or_abort(self, session: Session, app: str) -> Application:
        try:
            return self.load_application_fn(app, default_session=session)
        except ApplicationNotFoundError:
            self.echo_fn(
                f"""The account "{os.environ.get("AWS_PROFILE")}" does not contain the application "{app}"; ensure you have set the environment variable "AWS_PROFILE" correctly.""",
                fg="red",
            )
            raise click.Abort
