import json
import stat
import subprocess
from collections.abc import Callable
from pathlib import Path

import click
import requests
import yaml
from boto3 import Session

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import ApplicationException
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
        input: Callable[[str], str] = click.prompt,
        echo: Callable[[str], str] = click.secho,
        confirm: Callable[[str], bool] = click.confirm,
        load_application: Callable[[str], Application] = load_application,
        get_aws_session_or_abort: Callable[[str], Session] = get_aws_session_or_abort,
        check_codebase_exists: Callable[[str], str] = check_codebase_exists,
        check_image_exists: Callable[[str], str] = check_image_exists,
        get_build_url_from_arn: Callable[[str], str] = get_build_url_from_arn,
        list_latest_images: Callable[[str], str] = list_latest_images,
        start_build_extraction: Callable[[str], str] = start_build_extraction,
        check_if_commit_exists: Callable[[str], str] = check_if_commit_exists,
        run_subprocess: Callable[[str], str] = subprocess.run,
    ):
        self.input = input
        self.echo = echo
        self.confirm = confirm
        self.load_application = load_application
        self.get_aws_session_or_abort = get_aws_session_or_abort
        self.check_codebase_exists = check_codebase_exists
        self.check_image_exists = check_image_exists
        self.get_build_url_from_arn = get_build_url_from_arn
        self.list_latest_images = list_latest_images
        self.start_build_extraction = start_build_extraction
        self.check_if_commit_exists = check_if_commit_exists
        self.run_subprocess = run_subprocess

    def prepare(self):
        """Sets up an application codebase for use within a DBT platform
        project."""
        templates = setup_templates()

        repository = (
            self.run_subprocess(
                ["git", "remote", "get-url", "origin"], capture_output=True, text=True
            )
            .stdout.split("/")[-1]
            .strip()
            .removesuffix(".git")
        )
        if repository.endswith("-deploy") or Path("./copilot").exists():
            raise NotInCodeBaseRepositoryException()

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
        self.echo(
            mkfile(
                Path("."), ".copilot/image_build_run.sh", image_build_run_contents, overwrite=True
            )
        )

        image_build_run_file = Path(".copilot/image_build_run.sh")
        image_build_run_file.chmod(image_build_run_file.stat().st_mode | stat.S_IEXEC)

        self.echo(mkfile(Path("."), ".copilot/config.yml", config_contents, overwrite=True))

        for phase in ["build", "install", "post_build", "pre_build"]:
            phase_contents = templates.get_template(f".copilot/phases/{phase}.sh").render()

            self.echo(
                mkfile(Path("./.copilot"), f"phases/{phase}.sh", phase_contents, overwrite=True)
            )

    def build(self, app: str, codebase: str, commit: str):
        """Trigger a CodePipeline pipeline based build."""
        session = self.get_aws_session_or_abort()
        self.load_application(app, default_session=session)

        self.check_if_commit_exists(commit)

        codebuild_client = session.client("codebuild")
        build_url = self.__start_build_with_confirmation(
            self.confirm,
            codebuild_client,
            self.get_build_url_from_arn,
            f'You are about to build "{app}" for "{codebase}" with commit "{commit}". Do you want to continue?',
            {
                "projectName": f"codebuild-{app}-{codebase}",
                "artifactsOverride": {"type": "NO_ARTIFACTS"},
                "sourceVersion": commit,
            },
        )

        if build_url:
            return self.echo(
                f"Your build has been triggered. Check your build progress in the AWS Console: {build_url}"
            )

        raise ApplicationDeploymentNotTriggered(codebase)

    def deploy(self, app, env, codebase, commit):
        """Trigger a CodePipeline pipeline based deployment."""
        session = self.get_aws_session_or_abort()

        application = self.load_application(app, default_session=session)
        if not application.environments.get(env):
            raise ApplicationEnvironmentNotFoundException(env)

        self.check_codebase_exists(session, application, codebase)

        self.check_image_exists(session, application, codebase, commit)

        codebuild_client = session.client("codebuild")
        build_url = self.__start_build_with_confirmation(
            self.confirm,
            codebuild_client,
            self.get_build_url_from_arn,
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
            return self.echo(
                "Your deployment has been triggered. Check your build progress in the AWS Console: "
                f"{build_url}",
            )

        raise ApplicationDeploymentNotTriggered(codebase)

    def list(self, app: str, with_images: bool):
        """List available codebases for the application."""
        session = self.get_aws_session_or_abort()
        application = self.load_application(app, session)
        ssm_client = session.client("ssm")
        ecr_client = session.client("ecr")
        codebases = self.__get_codebases(application, ssm_client)

        self.echo("The following codebases are available:")

        for codebase in codebases:
            self.echo(f"- {codebase['name']} (https://github.com/{codebase['repository']})")
            if with_images:
                self.list_latest_images(
                    ecr_client,
                    f"{application.name}/{codebase['name']}",
                    codebase["repository"],
                    self.echo,
                )

        self.echo("")

    def __get_codebases(self, application, ssm_client):
        parameters = ssm_client.get_parameters_by_path(
            Path=f"/copilot/applications/{application.name}/codebases",
            Recursive=True,
        )["Parameters"]

        codebases = [json.loads(p["Value"]) for p in parameters]

        if not codebases:
            return []
        return codebases

    def __start_build_with_confirmation(
        self,
        confirm,
        codebuild_client,
        get_build_url_from_arn,
        confirmation_message,
        build_options,
    ):
        if confirm(confirmation_message):
            build_arn = self.start_build_extraction(codebuild_client, build_options)
            return get_build_url_from_arn(build_arn)
        return None


class ApplicationDeploymentNotTriggered(PlatformException):
    def __init__(self, codebase: str):
        super().__init__(f"""Your deployment for {codebase} was not triggered.""")


class ApplicationEnvironmentNotFoundException(ApplicationException):
    def __init__(self, environment: str):
        super().__init__(
            f"""The environment "{environment}" either does not exist or has not been deployed."""
        )


class NotInCodeBaseRepositoryException(PlatformException):
    def __init__(self):
        super().__init__(
            "You are in the deploy repository; make sure you are in the application codebase repository.",
        )
