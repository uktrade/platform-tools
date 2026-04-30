import time

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider


class ScheduledJobExecutionFailedException(PlatformException):
    pass


class JobManager:

    JOB_POLL_SECONDS = 5
    JOB_FINAL_STATUSES = {"SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"}

    def __init__(self, job_runner, io: ClickIOProvider = ClickIOProvider()):
        self.job_runner = job_runner
        self.io = io

    def start_execution(self, app: str, env: str, name: str, follow: bool):

        self.io.info(f"Beginning execution for job '{name}' in {app}/{env}...")
        execution_id = self.job_runner.run(name)
        self.io.info(f"Job started: {execution_id}")

        if follow:
            self.follow_execution(execution_id)

    def follow_execution(self, execution_id: str):

        self.io.info("Waiting for execution to finish...")

        while True:
            time.sleep(self.JOB_POLL_SECONDS)
            status = self.job_runner.get_status(execution_id)
            self.io.info(status)
            if status in self.JOB_FINAL_STATUSES:
                break

        if status == "SUCCEEDED":
            self.io.info(f"Job {execution_id} completed successfully.")
        else:
            raise ScheduledJobExecutionFailedException(
                f"Job {execution_id} finished with status {status}"
            )
