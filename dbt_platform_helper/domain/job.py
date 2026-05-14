import time

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.service import ServiceRepository


class ScheduledJobExecutionFailedException(PlatformException):
    pass


class JobManager:

    JOB_POLL_SECONDS = 5
    JOB_FINAL_STATUSES = {"SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"}

    def __init__(
        self,
        job_runner,
        service_repository: ServiceRepository = None,
        io: ClickIOProvider = ClickIOProvider(),
    ):
        self.job_runner = job_runner
        self.service_repository = service_repository
        self.io = io

    def start_execution(self, app: str, env: str, name: str, follow: bool):

        self.io.info(f"Beginning execution for job '{name}' in {app}/{env}...")
        execution_id = self.job_runner.run(name)
        self.io.info(f"Job started: {execution_id}")

        if follow:
            self.follow_execution(execution_id)

    def follow_execution(self, execution_id: str):

        self.io.info("Waiting for execution to finish...")
        start_time = time.monotonic()
        status = self.job_runner.get_status(execution_id)
        self.io.info(f"Status: {status}")

        while status not in self.JOB_FINAL_STATUSES:
            time.sleep(self.JOB_POLL_SECONDS)
            elapsed = int(time.monotonic() - start_time)
            status = self.job_runner.get_status(execution_id)
            self.io.info(f"Status: {status} ({elapsed}s elapsed)")

        if status == "SUCCEEDED":
            self.io.info(f"Job {execution_id} completed successfully.")
        else:
            raise ScheduledJobExecutionFailedException(
                f"Job {execution_id} finished with status {status}"
            )

    def list_jobs(self, app: str, env: str):
        jobs = [job.name for job in self.service_repository.list_jobs(app, env)]
        if jobs:
            self.io.info(
                f"Scheduled Jobs currently deployed for {app} in the {env} environment:\n{'\n'.join(jobs)}"
            )
        else:
            self.io.info(
                f"No Scheduled Jobs currently deployed for {app} in the {env} environment."
            )
