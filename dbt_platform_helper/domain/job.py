from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.step_functions import StepFunctions


class JobManager:
    def __init__(self, sfn_provider: StepFunctions, io: ClickIOProvider = ClickIOProvider()):
        self.sfn_provider = sfn_provider
        self.io = io

    def run(self, app: str, env: str, name: str):

        self.io.info(f"Beginning execution for job '{name}' in {app}/{env}...")
        state_machine_arn = self.sfn_provider.find_state_machine_arn(name)

        response = self.sfn_provider.start_execution(state_machine_arn)
        self.io.info(f"Job started:  {response['executionArn']}")
