import time

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.step_functions import StepFunctions


class ScheduledJobExecutionFailedException(PlatformException):
    pass


class JobManager:

    SECONDS = 5
    STATUSES = {"SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"}

    def __init__(self, sfn_provider: StepFunctions, io: ClickIOProvider = ClickIOProvider()):
        self.sfn_provider = sfn_provider
        self.io = io

    def run(self, app: str, env: str, name: str, follow: bool):

        self.io.info(f"Beginning execution for job '{name}' in {app}/{env}...")
        state_machine_arn = self.sfn_provider.find_state_machine_arn(name)

        response = self.sfn_provider.start_execution(state_machine_arn)
        execution_arn = response["executionArn"]
        self.io.info(f"Job started:  {response['executionArn']}")

        if follow:
            self.follow_execution(execution_arn)

    def follow_execution(self, execution_arn: str):

        self.io.info("Waiting for execution to finish...")

        while True:
            time.sleep(self.SECONDS)
            status = self.sfn_provider._get_status(execution_arn)
            self.io.info(status)
            if status in self.STATUSES:
                break

        if status == "SUCCEEDED":
            self.io.info(f"Job {execution_arn} completed successfully.")
        else:
            raise ScheduledJobExecutionFailedException(
                f"Job {execution_arn} finished with status {status}"
            )
