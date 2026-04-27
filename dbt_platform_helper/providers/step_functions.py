from typing import Optional

from botocore.exceptions import ClientError

from dbt_platform_helper.providers.aws.exceptions import AWSException


class StepFunctions:

    def __init__(self, sfn_client, application_name: str, env: str):
        self.sfn_client = sfn_client
        self.application_name = application_name
        self.env = env

    def find_state_machine_arn(self, job_name: str) -> Optional[str]:

        matches: list[str] = []
        paginator = self.sfn_client.get_paginator("list_state_machines")

        for page in paginator.paginate():
            for sm in page.get("stateMachines", []):
                arn = sm.get("stateMachineArn")
                tags = self._list_tags(arn)
                if (
                    tags.get("copilot-application") == self.application_name
                    and tags.get("copilot-environment") == self.env
                    and tags.get("copilot-service") == job_name
                ):
                    matches.append(arn)

        if not matches:
            raise StateMachineNotFoundException(self.application_name, self.env, job_name)
        if len(matches) > 1:
            raise MultipleStateMachinesFoundException(
                self.application_name, self.env, job_name, matches
            )
        return matches[0]

    def start_execution(self, state_machine_arn: str, name: Optional[str] = None) -> str:
        kwargs = {"stateMachineArn": state_machine_arn}
        if name:
            kwargs["name"] = name

        try:
            result = self.sfn_client.start_execution(**kwargs)
            return result

        except ClientError as err:
            raise StartExecutionFailedException(
                state_machine_arn, err.response.get("Error", {}).get("Message", str(err))
            )

    def _list_tags(self, resource_arn: str) -> dict:
        response = self.sfn_client.list_tags_for_resource(resourceArn=resource_arn)
        return {tag["key"]: tag["value"] for tag in response.get("tags", [])}

    def _get_status(self, execution_arn: str):
        response = self.sfn_client.describe_execution(executionArn=execution_arn)
        return response["status"]


class StateMachineNotFoundException(AWSException):
    def __init__(self, application_name: str, environment: str, job_name: str):
        super().__init__(
            f"Scheduled Job '{job_name}' not found in '{environment}' of application '{application_name}'.\n"
            f"Please check that the combination of application, environment and scheduled job are correct."
        )


class StartExecutionFailedException(AWSException):
    def __init__(self, state_machine_arn: str, error: str):
        super().__init__(
            f"Failed to start the Scheduled Job execution.\n"
            f"AWS returned: {error}\n"
            f"State Machine ARN: {state_machine_arn}."
        )


class MultipleStateMachinesFoundException(AWSException):
    def __init__(
        self, application_name: str, environment: str, job_name: str, state_machine_arns: list[str]
    ):
        super().__init__(
            f"Multiple Jobs {len(state_machine_arns)} with the name '{job_name}' found in '{environment}'\n"
            f"Expected 1 job\n"
            f"This usually means that they share the same tags\n"
            f"Found ARNs: {state_machine_arns}"
        )
