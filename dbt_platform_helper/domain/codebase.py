import json
import os
import stat
import subprocess
from collections.abc import Callable
from pathlib import Path

import click
import requests
import yaml
from boto3 import Session

from dbt_platform_helper.exceptions import AWSException
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import ApplicationNotFoundError
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.aws import check_codebase_exists, get_aws_session_or_abort
from dbt_platform_helper.utils.files import mkfile
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
        subprocess: Callable[[str], str] = subprocess.run,
    ):
        self.input_fn = input_fn
        self.echo_fn = echo_fn
        self.confirm_fn = confirm_fn
        self.load_application_fn = load_application_fn
        self.get_aws_session_or_abort_fn = get_aws_session_or_abort_fn
        self.check_codebase_exists_fn = check_codebase_exists
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
            self.echo_fn(
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
        self.__load_application_or_abort(session, app)

        check_if_commit_exists = self.subprocess(
            ["git", "branch", "-r", "--contains", f"{commit}"], capture_output=True, text=True
        )

        if check_if_commit_exists.stderr:
            self.echo_fn(
                f'The commit hash "{commit}" either does not exist or you need to run `git fetch`.',
                fg="red",
            )
            raise SystemExit(1)

        codebuild_client = session.client("codebuild")
        build_url = self.__start_build_with_confirmation(
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

    def deploy(self, app, env, codebase, commit):
        """Trigger a CodePipeline pipeline based deployment."""
        session = self.get_aws_session_or_abort_fn()
        application = self.__load_application_with_environment(session, app, env)
        self.__check_codebase_exists(session, application, codebase)
        self.__check_image_exists(session, application, codebase, commit)

        codebuild_client = session.client("codebuild")
        build_url = self.__start_build_with_confirmation(
            codebuild_client,
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

        return self.echo_fn("Your deployment was not triggered.")

    def list(self, app: str, with_images: bool):
        """List available codebases for the application."""
        session = self.get_aws_session_or_abort_fn()
        application = self.__load_application_or_abort(session, app)
        ssm_client = session.client("ssm")
        ecr_client = session.client("ecr")
        parameters = ssm_client.get_parameters_by_path(
            Path=f"/copilot/applications/{application.name}/codebases",
            Recursive=True,
        )["Parameters"]

        codebases = [json.loads(p["Value"]) for p in parameters]

        if not codebases:
            self.echo_fn(f'No codebases found for application "{application.name}"', fg="red")
            raise SystemExit(1)

        self.echo_fn("The following codebases are available:")

        for codebase in codebases:
            self.echo_fn(f"- {codebase['name']} (https://github.com/{codebase['repository']})")
            if with_images:
                self._list_latest_images(
                    ecr_client, f"{application.name}/{codebase['name']}", codebase["repository"]
                )

        self.echo_fn("")

    def __get_build_url_from_arn(self, build_arn: str) -> str:
        _, _, _, region, account_id, project_name, build_id = build_arn.split(":")
        project_name = project_name.removeprefix("build/")
        return (
            f"https://eu-west-2.console.aws.amazon.com/codesuite/codebuild/{account_id}/projects/"
            f"{project_name}/build/{project_name}%3A{build_id}"
        )

    def __load_application_or_abort(self, session: Session, app: str) -> Application:
        try:
            return self.load_application_fn(app, default_session=session)
        except ApplicationNotFoundError:
            self.echo_fn(
                f"""The account "{os.environ.get("AWS_PROFILE")}" does not contain the application "{app}"; ensure you have set the environment variable "AWS_PROFILE" correctly.""",
                fg="red",
            )
            raise click.Abort

    def __load_application_with_environment(self, session: Session, app, env):
        application = self.__load_application_or_abort(session, app)

        if not application.environments.get(env):
            self.echo_fn(
                f"""The environment "{env}" either does not exist or has not been deployed.""",
                fg="red",
            )
            raise click.Abort
        return application

    def __check_codebase_exists(self, session: Session, application: Application, codebase: str):
        try:
            json.loads(self.check_codebase_exists_fn(session, application, codebase))
        except (
            AWSException,
            json.JSONDecodeError,
        ):
            self.echo_fn(
                f"""The codebase "{codebase}" either does not exist or has not been deployed.""",
                fg="red",
            )
            raise click.Abort

    def __check_image_exists(
        self, session: Session, application: Application, codebase: str, commit: str
    ):
        ecr_client = session.client("ecr")
        try:
            ecr_client.describe_images(
                repositoryName=f"{application.name}/{codebase}",
                imageIds=[{"imageTag": f"commit-{commit}"}],
            )
        except ecr_client.exceptions.RepositoryNotFoundException:
            self.echo_fn(
                f'The ECR Repository for codebase "{codebase}" does not exist.',
                fg="red",
            )
            raise click.Abort
        except ecr_client.exceptions.ImageNotFoundException:
            self.echo_fn(
                f'The commit hash "{commit}" has not been built into an image, try the '
                "`platform-helper codebase build` command first.",
                fg="red",
            )
            raise click.Abort

    def __start_build_with_confirmation(
        self, codebuild_client, confirmation_message, build_options
    ):
        if self.confirm_fn(confirmation_message):
            response = codebuild_client.start_build(**build_options)
            return self.__get_build_url_from_arn(response["build"]["arn"])

    def _list_latest_images(self, ecr_client, ecr_repository_name, codebase_repository):
        paginator = ecr_client.get_paginator("describe_images")
        describe_images_response_iterator = paginator.paginate(
            repositoryName=ecr_repository_name,
            filter={"tagStatus": "TAGGED"},
        )
        images = []
        for page in describe_images_response_iterator:
            images += page["imageDetails"]

        sorted_images = sorted(
            images,
            key=lambda i: i["imagePushedAt"],
            reverse=True,
        )

        MAX_RESULTS = 20

        for image in sorted_images[:MAX_RESULTS]:
            try:
                commit_tag = next(t for t in image["imageTags"] if t.startswith("commit-"))
                if not commit_tag:
                    continue

                commit_hash = commit_tag.replace("commit-", "")
                self.echo_fn(
                    f"  - https://github.com/{codebase_repository}/commit/{commit_hash} - published: {image['imagePushedAt']}"
                )
            except StopIteration:
                continue
