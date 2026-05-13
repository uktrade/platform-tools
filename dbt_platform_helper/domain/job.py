import time

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.parameter_store import ParameterStore


class ScheduledJobExecutionFailedException(PlatformException):
    pass


class JobManager:

    JOB_POLL_SECONDS = 5
    JOB_FINAL_STATUSES = {"SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"}

    def __init__(self, job_runner, parameter_store: ParameterStore, io: ClickIOProvider = ClickIOProvider()):
        self.job_runner = job_runner
        self.parameter_store = parameter_store
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
        # /platform/applications/demodjango/environments/ben/services/api
        service_parameter_names = self.parameter_store.list_parameters_by_name_starts_with(f"/platform/applications/{app}/environments/{env}/services/")
        jobs = []
        for param_name in service_parameter_names:
            service = self.parameter_store.get_ssm_parameter_by_name(param_name)
            if service.value.get("type") == "Scheduled Job":
                jobs.append(service.value.get("name"))
        if jobs:
            self.io.info(f"Scheduled Jobs currently deployed for {app} in the {env} environment:\n{"\n".join(jobs)}")
        else:
            self.io.info(f"No Scheduled Jobs currently deployed for {app} in the {env} environment.")
            
        
