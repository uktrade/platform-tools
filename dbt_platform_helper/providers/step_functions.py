from botocore.exceptions import ClientError

from dbt_platform_helper.providers.aws.exceptions import AWSException


class StepFunctions:

    def __init__(self, sfn_client, application_name: str, env: str, account_id: str):
        self.sfn_client = sfn_client
        self.application_name = application_name
        self.env = env
        self.account_id = account_id

    def run(self, job_name: str) -> str:
        state_machine_arn = self._build_state_machine_arn(job_name)
        try:
            response = self.sfn_client.start_execution(stateMachineArn=state_machine_arn)
        except ClientError as err:
            error_code = err.response.get("Error", {}).get("Code")
            if error_code == "StateMachineDoesNotExist":
                raise StateMachineNotFoundException(self.application_name, self.env, job_name)
            raise StartExecutionFailedException(
                state_machine_arn, err.response.get("Error", {}).get("Message", str(err))
            )
        return response["executionArn"]

    def get_status(self, execution_arn: str):
        try:
            response = self.sfn_client.describe_execution(executionArn=execution_arn)
        except ClientError as err:
            raise GetExecutionStatusFailedException(
                err.response.get("Error", {}).get("Message", str(err))
            )
        return response["status"]

    def _build_state_machine_arn(self, job_name: str) -> str:
        region = self.sfn_client.meta.region_name
        state_machine_name = f"{self.application_name}-{self.env}-{job_name}-sfn"
        return f"arn:aws:states:{region}:{self.account_id}:stateMachine:{state_machine_name}"


class StateMachineNotFoundException(AWSException):
    def __init__(self, application_name: str, environment: str, job_name: str):
        super().__init__(
            f"Scheduled Job '{job_name}' not found in '{environment}' of application '{application_name}'.\n"
            f"Please check that the combination of application, environment and name correctly describe a deployed scheduled job."
        )


class StartExecutionFailedException(AWSException):
    def __init__(self, state_machine_arn: str, error: str):
        super().__init__(f"Failed to start the Scheduled Job execution. {error}")


class GetExecutionStatusFailedException(AWSException):
    def __init__(self, error: str):
        super().__init__(f"Failed to get status for Scheduled Job. {error}")
