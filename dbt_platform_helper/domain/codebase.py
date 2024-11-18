import json
import stat
import subprocess
from collections.abc import Callable
from pathlib import Path

import click
import requests
import yaml
from boto3 import Session

from dbt_platform_helper.exceptions import ApplicationDeploymentNotTriggered
from dbt_platform_helper.exceptions import ApplicationEnvironmentNotFoundError
from dbt_platform_helper.exceptions import NoCopilotCodebasesFoundError
from dbt_platform_helper.exceptions import NotInCodeBaseRepositoryError
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.aws import check_codebase_exists
from dbt_platform_helper.utils.aws import check_image_exists
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.aws import get_build_url_from_arn
from dbt_platform_helper.utils.aws import list_latest_images
from dbt_platform_helper.utils.aws import start_build_extraction
from dbt_platform_helper.utils.files import mkfile
from dbt_platform_helper.utils.git import check_if_commit_exists
from dbt_platform_helper.utils.template import setup_templates


class Codebase:
    def __init__(
        self,
        input_fn: Callable[[str], str] = click.prompt,
        echo_fn: Callable[[str], str] = click.secho,
        confirm_fn: Callable[[str], bool] = click.confirm,
        load_application_fn: Callable[[str], Application] = load_application,
        get_aws_session_or_abort_fn: Callable[[str], Session] = get_aws_session_or_abort,
        check_codebase_exists_fn: Callable[[str], str] = check_codebase_exists,
        check_image_exists_fn: Callable[[str], str] = check_image_exists,
        get_build_url_from_arn_fn: Callable[[str], str] = get_build_url_from_arn,
        list_latest_images_fn: Callable[[str], str] = list_latest_images,
        start_build_extraction_fn: Callable[[str], str] = start_build_extraction,
        check_if_commit_exists_fn: Callable[[str], str] = check_if_commit_exists,
        subprocess: Callable[[str], str] = subprocess.run,
    ):
        self.input_fn = input_fn
        self.echo_fn = echo_fn
        self.confirm_fn = confirm_fn
        self.load_application_fn = load_application_fn
        self.get_aws_session_or_abort_fn = get_aws_session_or_abort_fn
        self.check_codebase_exists_fn = check_codebase_exists_fn
        self.check_image_exists_fn = check_image_exists_fn
        self.get_build_url_from_arn_fn = get_build_url_from_arn_fn
        self.list_latest_images_fn = list_latest_images_fn
        self.start_build_extraction_fn = start_build_extraction_fn
        self.check_if_commit_exists_fn = check_if_commit_exists_fn
        self.subprocess = subprocess

    def prepare(self):
        """Sets up an application codebase for use within a DBT platform
        project."""
        templates = setup_templates()

        repository = (
            self.subprocess(["git", "remote", "get-url", "origin"], capture_output=True, text=True)
            .stdout.split("/")[-1]
            .strip()
            .removesuffix(".git")
        )
        if repository.endswith("-deploy") or Path("./copilot").exists():
            raise NotInCodeBaseRepositoryError

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
        builder_version = min(builder_version, "0.4.240")

        Path("./.copilot/phases").mkdir(parents=True, exist_ok=True)
        image_build_run_contents = templates.get_template(f".copilot/image_build_run.sh").render()

        config_contents = templates.get_template(f".copilot/config.yml").render(
            repository=repository, builder_version=builder_version
        )
        self.echo_fn(
            mkfile(
                Path("."), ".copilot/image_build_run.sh", image_build_run_contents, overwrite=True
            )
        )

        image_build_run_file = Path(".copilot/image_build_run.sh")
        image_build_run_file.chmod(image_build_run_file.stat().st_mode | stat.S_IEXEC)

        self.echo_fn(mkfile(Path("."), ".copilot/config.yml", config_contents, overwrite=True))

        for phase in ["build", "install", "post_build", "pre_build"]:
            phase_contents = templates.get_template(f".copilot/phases/{phase}.sh").render()

            self.echo_fn(
                mkfile(Path("./.copilot"), f"phases/{phase}.sh", phase_contents, overwrite=True)
            )

    def build(self, app: str, codebase: str, commit: str):
        """Trigger a CodePipeline pipeline based build."""
        session = self.get_aws_session_or_abort_fn()
        self.load_application_fn(app, default_session=session)

        self.check_if_commit_exists_fn(commit)

        codebuild_client = session.client("codebuild")
        build_url = self.__start_build_with_confirmation(
            self.confirm_fn,
            codebuild_client,
            self.get_build_url_from_arn_fn,
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

        raise ApplicationDeploymentNotTriggered()

    def deploy(self, app, env, codebase, commit):
        """Trigger a CodePipeline pipeline based deployment."""
        session = self.get_aws_session_or_abort_fn()

        application = self.load_application_fn(app, default_session=session)
        if not application.environments.get(env):
            raise ApplicationEnvironmentNotFoundError()

        json.loads(self.check_codebase_exists_fn(session, application, codebase))

        self.check_image_exists_fn(session, application, codebase, commit)

        codebuild_client = session.client("codebuild")
        build_url = self.__start_build_with_confirmation(
            self.confirm_fn,
            codebuild_client,
            self.get_build_url_from_arn_fn,
            f'You are about to deploy "{app}" for "{codebase}" with commit "{commit}" to the "{env}" environment. Do you want to continue?',
            {
                "projectName": f"pipeline-{application.name}-{codebase}-BuildProject",
                "artifactsOverride": {"type": "NO_ARTIFACTS"},
                "sourceTypeOverride": "NO_SOURCE",
                "environmentVariablesOverride": [
                    {"name": "COPILOT_ENVIRONMENT", "value": env},
                    {"name": "IMAGE_TAG", "value": f"commit-{commit}"},
                ],
            },
        )

        if build_url:
            return self.echo_fn(
                "Your deployment has been triggered. Check your build progress in the AWS Console: "
                f"{build_url}",
            )

        raise ApplicationDeploymentNotTriggered()

    def list(self, app: str, with_images: bool):
        """List available codebases for the application."""
        session = self.get_aws_session_or_abort_fn()
        application = self.load_application_fn(app, session)
        ssm_client = session.client("ssm")
        ecr_client = session.client("ecr")
        codebases = self.__get_codebases(application, ssm_client)

        self.echo_fn("The following codebases are available:")

        for codebase in codebases:
            self.echo_fn(f"- {codebase['name']} (https://github.com/{codebase['repository']})")
            if with_images:
                self.list_latest_images_fn(
                    ecr_client,
                    f"{application.name}/{codebase['name']}",
                    codebase["repository"],
                    self.echo_fn,
                )

        self.echo_fn("")

    # TODO return empty list without exception
    def __get_codebases(self, application, ssm_client):
        parameters = ssm_client.get_parameters_by_path(
            Path=f"/copilot/applications/{application.name}/codebases",
            Recursive=True,
        )["Parameters"]

        codebases = [json.loads(p["Value"]) for p in parameters]

        if not codebases:
            raise NoCopilotCodebasesFoundError
        return codebases

    def __start_build_with_confirmation(
        self,
        confirm_fn,
        codebuild_client,
        get_build_url_from_arn_fn,
        confirmation_message,
        build_options,
    ):
        if confirm_fn(confirmation_message):
            build_arn = self.start_build_extraction_fn(codebuild_client, build_options)
            return get_build_url_from_arn_fn(build_arn)
        return None
