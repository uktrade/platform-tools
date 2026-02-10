import json
import stat
import subprocess
import time
from abc import ABC
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple

import requests
import yaml
from boto3 import Session
from prettytable import PrettyTable

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.ports.config import ConfigPort
from dbt_platform_helper.ports.deployed import DeploymentPort
from dbt_platform_helper.ports.deployed import PipelineDetails
from dbt_platform_helper.ports.deployed import PipelinePort
from dbt_platform_helper.ports.deployed import PipelineStatus
from dbt_platform_helper.ports.file_system import FileSystemPort
from dbt_platform_helper.providers.ecr import ECRProvider
from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.parameter_store import ParameterStore
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import (
    ApplicationEnvironmentNotFoundException,
)
from dbt_platform_helper.utils.application import load_application
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.aws import get_build_url_from_arn
from dbt_platform_helper.utils.aws import get_build_url_from_pipeline_execution_id
from dbt_platform_helper.utils.aws import get_image_build_project
from dbt_platform_helper.utils.aws import get_manual_release_pipeline
from dbt_platform_helper.utils.aws import list_latest_images
from dbt_platform_helper.utils.aws import start_build_extraction
from dbt_platform_helper.utils.aws import start_pipeline_and_return_execution_id
from dbt_platform_helper.utils.template import setup_templates


@dataclass
class Deployment(ABC):
    codebase: str
    pipeline: str
    tag: str
    execution_id: str


@dataclass
class RedployResult(ABC):
    codebase: str
    pipeline: str
    execution_id: Optional[str]
    status: str
    tag: Optional[str]
    error: Optional[str] = None
    url: Optional[str] = None


class Codebase:
    def __init__(
        self,
        parameter_provider: ParameterStore,
        io: ClickIOProvider = ClickIOProvider(),
        load_application: Callable[[str], Application] = load_application,
        get_aws_session_or_abort: Callable[[str], Session] = get_aws_session_or_abort,
        ecr_provider: ECRProvider = ECRProvider(),
        get_image_build_project: Callable[[str], str] = get_image_build_project,
        get_manual_release_pipeline: Callable[[str], str] = get_manual_release_pipeline,
        get_build_url_from_arn: Callable[[str], str] = get_build_url_from_arn,
        get_build_url_from_pipeline_execution_id: Callable[
            [str], str
        ] = get_build_url_from_pipeline_execution_id,
        list_latest_images: Callable[[str], str] = list_latest_images,
        start_build_extraction: Callable[[str], str] = start_build_extraction,
        start_pipeline_and_return_execution_id: Callable[
            [str], str
        ] = start_pipeline_and_return_execution_id,
        run_subprocess: Callable[[str], str] = subprocess.run,
        config: ConfigPort = None,
        deployment: DeploymentPort = None,
        pipeline: PipelinePort = None,
        file_system: FileSystemPort = None,
    ):
        self.parameter_provider = parameter_provider
        self.io = io
        self.load_application = load_application
        self.get_aws_session_or_abort = get_aws_session_or_abort
        self.ecr_provider = ecr_provider
        self.get_image_build_project = get_image_build_project
        self.get_manual_release_pipeline = get_manual_release_pipeline
        self.get_build_url_from_arn = get_build_url_from_arn
        self.get_build_url_from_pipeline_execution_id = get_build_url_from_pipeline_execution_id
        self.list_latest_images = list_latest_images
        self.start_build_extraction = start_build_extraction
        self.start_pipeline_and_return_execution_id = start_pipeline_and_return_execution_id
        self.run_subprocess = run_subprocess
        self.config = config
        self.deployment = deployment
        self.pipeline = pipeline
        self.file_system = file_system

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
        self.io.info(
            FileProvider.mkfile(
                Path("."), ".copilot/image_build_run.sh", image_build_run_contents, overwrite=True
            )
        )

        image_build_run_file = Path(".copilot/image_build_run.sh")
        image_build_run_file.chmod(image_build_run_file.stat().st_mode | stat.S_IEXEC)

        self.io.info(
            FileProvider.mkfile(Path("."), ".copilot/config.yml", config_contents, overwrite=True)
        )

        for phase in ["build", "install", "post_build", "pre_build"]:
            phase_contents = templates.get_template(f".copilot/phases/{phase}.sh").render()

            self.io.info(
                FileProvider.mkfile(
                    Path("./.copilot"), f"phases/{phase}.sh", phase_contents, overwrite=True
                )
            )

    def build(self, app: str, codebase: str, commit: str):
        """Trigger a CodePipeline pipeline based build."""
        session = self.get_aws_session_or_abort()
        self.load_application(app, default_session=session)

        codebuild_client = session.client("codebuild")
        project_name = self.get_image_build_project(codebuild_client, app, codebase)
        build_url = self.__start_build_with_confirmation(
            codebuild_client,
            self.get_build_url_from_arn,
            f'You are about to build "{app}" for "{codebase}" with commit "{commit}". Do you want to continue?',
            {
                "projectName": project_name,
                "artifactsOverride": {"type": "NO_ARTIFACTS"},
                "sourceVersion": commit,
            },
        )

        if build_url:
            return self.io.info(
                f"Your build has been triggered. Check your build progress in the AWS Console: {build_url}"
            )

        raise ApplicationDeploymentNotTriggered(codebase)

    def deploy(
        self,
        app: str,
        env: str,
        codebase: str,
        commit: str = None,
        tag: str = None,
        branch: str = None,
    ):
        """Trigger a CodePipeline pipeline based deployment."""

        self._validate_reference_flags(commit, tag, branch)

        application, session = self._populate_application_values(app, env)

        image_ref = None
        if commit:
            self._validate_sha_length(commit)
            image_ref = f"commit-{commit}"
        elif tag:
            image_ref = f"tag-{tag}"
        elif branch:
            image_ref = f"branch-{branch}"

        image_ref = self.ecr_provider.get_commit_tag_for_reference(
            application.name, codebase, image_ref
        )

        codepipeline_client = session.client("codepipeline")
        pipeline_name = self.get_manual_release_pipeline(codepipeline_client, app, codebase)

        corresponding_to = ""
        if tag:
            corresponding_to = f"(corresponding to tag {tag}) "
        elif branch:
            corresponding_to = f"(corresponding to branch {branch}) "

        confirmation_message = f'\nYou are about to deploy "{app}" for "{codebase}" with image reference "{image_ref}" {corresponding_to}to the "{env}" environment using the "{pipeline_name}" deployment pipeline. Do you want to continue?'
        build_options = {
            "name": pipeline_name,
            "variables": [
                {"name": "ENVIRONMENT", "value": env},
                {"name": "IMAGE_TAG", "value": image_ref},
            ],
        }

        build_url = self.__start_pipeline_execution_with_confirmation(
            codepipeline_client,
            self.get_build_url_from_pipeline_execution_id,
            confirmation_message,
            build_options,
        )

        if build_url:
            return self.io.info(
                "Your deployment has been triggered. Check your build progress in the AWS Console: "
                f"{build_url}",
            )

        raise ApplicationDeploymentNotTriggered(codebase)

    def _validate_reference_flags(self, commit: str, tag: str, branch: str):
        provided = [ref for ref in [commit, tag, branch] if ref]

        if len(provided) == 0:
            self.io.abort_with_error(
                "To deploy, you must provide one of the options --commit, --tag or --branch."
            )
        elif len(provided) > 1:
            self.io.abort_with_error(
                "You have provided more than one of the --tag, --branch and --commit options but these are mutually exclusive. Please provide only one of these options."
            )

    def _populate_application_values(self, app: str, env: str) -> Tuple[Application, Session]:
        session = self.get_aws_session_or_abort()
        application = self.load_application(app, default_session=session)
        if not application.environments.get(env):
            raise ApplicationEnvironmentNotFoundException(application.name, env)
        return application, session

    def list(self, app: str, with_images: bool):
        """List available codebases for the application."""
        session = self.get_aws_session_or_abort()
        application = self.load_application(app, session)
        ecr_client = session.client("ecr")
        codebases = self.__get_codebases(application, session.client("ssm"))

        self.io.info("The following codebases are available:")

        for codebase in codebases:
            self.io.info(f"- {codebase['name']} (https://github.com/{codebase['repository']})")
            if with_images:
                self.list_latest_images(
                    ecr_client,
                    f"{application.name}/{codebase['name']}",
                    codebase["repository"],
                    self.io.info,
                )

        self.io.info("")

    def __get_codebases(self, application, ssm_client):
        parameters = self.parameter_provider.get_ssm_parameters_by_path(
            f"/copilot/applications/{application.name}/codebases"
        )
        codebases = [json.loads(p["Value"]) for p in parameters]

        if not codebases:
            return []
        return codebases

    def __start_build_with_confirmation(
        self,
        codebuild_client,
        get_build_url_from_arn,
        confirmation_message,
        build_options,
    ):
        if self.io.confirm(confirmation_message):
            build_arn = self.start_build_extraction(codebuild_client, build_options)
            return get_build_url_from_arn(build_arn)
        return None

    def __start_pipeline_execution_with_confirmation(
        self,
        codepipeline_client,
        get_build_url_from_pipeline_execution_id,
        confirmation_message,
        build_options,
    ):
        if self.io.confirm(confirmation_message):
            execution_id = self.start_pipeline_and_return_execution_id(
                codepipeline_client, build_options
            )
            return get_build_url_from_pipeline_execution_id(execution_id, build_options["name"])
        return None

    def _validate_sha_length(self, commit):
        if len(commit) < 7:
            self.io.abort_with_error(
                "Your commit reference is too short. Commit sha hashes specified by '--commit' must be at least 7 characters long."
            )

    def redeploy(
        self,
        app: str,
        env: str,
        codebases: List[str],
        wait: bool = True,
        poll_interval: int = 60,
        wait_timeout: int = 1800,
    ) -> List[RedployResult]:

        service_to_codebase = {}
        codebase_tags = defaultdict(set)
        mismatched_commits = []
        deployments: List[Deployment] = []
        results = []

        cwd = self.file_system.get_current_directory()
        if not codebases and "-deploy" not in cwd.parts[-1]:
            raise PlatformException("Not in deploy repo")

        config = self.config.load_and_validate_platform_config()
        codebase_pipelines = config.get("codebase_pipelines", {})
        if not codebases:
            codebases = codebase_pipelines.keys()

        for codebase in codebases:
            codebase_config = codebase_pipelines.get(codebase, {})
            for run_group in codebase_config.get("services", []):
                for _, services in run_group.items():
                    for service in services:
                        service_to_codebase[service] = codebase

        services = self.deployment.get_deployed_services(app, env)

        for service in services:
            codebase = service_to_codebase.get(service.name, "")
            if codebase:
                codebase_tags[codebase].add(service.tag)

        for codebase, deployed_commits in codebase_tags.items():
            if len(deployed_commits) > 1:
                mismatched_commits.append((codebase, deployed_commits))

        if mismatched_commits:
            message = "Commit mismatch on deployed services for the following codebases:\n"
            for codebase in mismatched_commits:
                message += f"- {codebase[0]}\n"
            raise PlatformException(message)

        for codebase, deployed_tags in codebase_tags.items():
            tag = deployed_tags.pop()

            pipeline_name = f"{app}-{codebase}-manual-release"
            # TODO can be removed when no one has copilot pipelines
            if not self.pipeline.pipeline_exists(pipeline_name):
                pipeline_name += "-pipeline"

            confirmation_message = f'\nFor the application "{app}", you are about to redeploy the codebase "{codebase}" with image reference "{tag}" (corresponding to the "{env}" environment using the "{pipeline_name}" deployment pipeline. Do you want to continue?'

            if self.io.confirm(confirmation_message):
                execution_id = self.pipeline.trigger_deployment(
                    PipelineDetails(
                        name=pipeline_name,
                        image_tag=tag,
                        environment=env,
                    )
                )

                if execution_id:
                    deployments.append(
                        Deployment(
                            codebase=codebase,
                            pipeline=pipeline_name,
                            execution_id=execution_id,
                            tag=tag,
                        )
                    )
                else:
                    results.append(
                        RedployResult(
                            codebase=codebase,
                            pipeline=pipeline_name,
                            execution_id=None,
                            status="not triggered",
                            tag=tag,
                            error="Pipeline trigger failed",
                        )
                    )

        if deployments and wait:
            completed_results = self._wait_for_all_pipelines(
                deployments, poll_interval, wait_timeout
            )
            results.extend(completed_results)
        else:
            for deployment in deployments:
                results.append(
                    RedployResult(
                        codebase=deployment.codebase,
                        pipeline=deployment.pipeline,
                        execution_id=deployment.execution_id,
                        status="triggered",
                        tag=deployment.tag,
                        url=self.pipeline.get_pipeline_url(
                            deployment.pipeline, deployment.execution_id
                        ),
                    )
                )
        return results

    def _wait_for_all_pipelines(
        self, deployments: List[Deployment], poll_interval: int, wait_timeout: int
    ) -> List[RedployResult]:
        start_time = time.time()
        pending: Set[str] = {deployment.pipeline for deployment in deployments}
        pipeline_map = {deployment.pipeline: deployment for deployment in deployments}
        results = []

        while pending:
            elapsed = time.time() - start_time
            if elapsed > wait_timeout:
                for pipeline in list(pending):
                    deployment = pipeline_map[pipeline]
                    execution = self.pipeline.get_execution_status(
                        pipeline, execution_id=deployment.execution_id
                    )
                    if execution:
                        status = execution.status.value.lower()
                        error = "Timeout" if not execution.is_complete else None
                    else:
                        status = "Unknown"
                        error = "Failed to get status"

                    results.append(
                        RedployResult(
                            codebase=deployment.codebase,
                            pipeline=deployment.pipeline,
                            execution_id=deployment.execution_id,
                            status=status,
                            tag=deployment.tag,
                            error=error,
                        )
                    )
                break
            for pipeline in list(pending):
                deployment = pipeline_map[pipeline]
                execution = self.pipeline.get_execution_status(
                    pipeline, execution_id=deployment.execution_id
                )
                if execution and execution.is_complete:
                    results.append(
                        RedployResult(
                            codebase=deployment.codebase,
                            pipeline=deployment.pipeline,
                            execution_id=deployment.execution_id,
                            status=execution.status.value.lower(),
                            tag=deployment.tag,
                            error=None if execution.is_successful else "Pipeline failed",
                        )
                    )
                    pending.remove(pipeline)

                if pending:
                    self.io.info(f"Executions for {pending} still pending ...")
                    time.sleep(poll_interval)

        return results


class ApplicationDeploymentNotTriggered(PlatformException):
    def __init__(self, codebase: str):
        super().__init__(f"""Your deployment for {codebase} was not triggered.""")


class NotInCodeBaseRepositoryException(PlatformException):
    def __init__(self):
        super().__init__(
            "You are in the deploy repository; make sure you are in the application codebase repository.",
        )


class RedeployDisplay:

    def format_results(self, results: List[RedployResult], waiting: bool) -> str:
        if waiting:
            return self._format_with_status(results)
        else:
            return self._format_with_url(results)

    def _format_with_status(self, results: List[RedployResult]):
        table = PrettyTable()
        field_names = ["Codebase", "Tag", "Status", "Exec ID", "Error"]
        table.field_names = field_names

        for name in field_names:
            table.align[name] = "l"

        for result in results:
            table.add_row(
                [
                    result.codebase,
                    result.tag,
                    result.status,
                    self._format_execution_id(result.execution_id),
                    self._format_error(result.error),
                ]
            )
        return str(table)

    def _format_with_url(self, results: List[RedployResult]):
        table = PrettyTable()
        field_names = ["Codebase", "Tag", "Exec ID", "Url"]
        table.field_names = field_names

        for name in field_names:
            table.align[name] = "l"
        table.max_width["Url"] = 125
        for result in results:
            table.add_row(
                [
                    result.codebase,
                    result.tag,
                    self._format_execution_id(result.execution_id),
                    result.url,
                ]
            )

        return str(table)

    def format_summary(self, results: List[RedployResult], waiting: bool) -> str:
        if waiting:
            succeeded = sum(
                1 for result in results if result.status == PipelineStatus.SUCCEEDED.value.lower()
            )
            failed = sum(
                1
                for result in results
                if result.status in [PipelineStatus.FAILED.value.lower(), "not triggered"]
            )
            in_progress = sum(
                1 for result in results if result.status == PipelineStatus.IN_PROGRESS.value.lower()
            )
            return (
                "\nSummary: "
                f"{succeeded} succeeded, "
                f"{failed} failed, "
                f"{in_progress} in_progress, "
            )
        else:
            triggered = sum(1 for result in results if result.execution_id)
            not_triggered = len(results) - triggered

            return "\nSummary: " f"{triggered} triggered, " f"{not_triggered} failed to trigger"

    def _format_execution_id(self, execution_id: str) -> str:
        return execution_id[:8] + "..." if len(execution_id) > 8 else execution_id

    def _format_error(self, error: Optional[str]) -> str:

        if not error:
            return "-"

        if len(error) > 40:
            return error[: 40 - 3] + "..."

        return error
