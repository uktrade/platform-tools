import json

import botocore
from cfn_tools import dump_yaml
from cfn_tools import load_yaml

from dbt_platform_helper.platform_exception import PlatformException


class CloudFormation:
    # TODO: DBTP-1966: add handling for optional client parameters to handle case of calling boto API with None
    def __init__(self, cloudformation_client, iam_client=None, ssm_client=None):
        self.cloudformation_client = cloudformation_client
        self.iam_client = iam_client
        self.ssm_client = ssm_client

    def add_stack_delete_policy_to_task_role(self, task_name: str):
        stack_name = f"task-{task_name}"
        stack_resources = self.cloudformation_client.list_stack_resources(StackName=stack_name)[
            "StackResourceSummaries"
        ]

        for resource in stack_resources:
            if resource["LogicalResourceId"] == "DefaultTaskRole":
                task_role_name = resource["PhysicalResourceId"]
                self.iam_client.put_role_policy(
                    RoleName=task_role_name,
                    PolicyName="DeleteCloudFormationStack",
                    PolicyDocument=json.dumps(
                        {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Action": ["cloudformation:DeleteStack"],
                                    "Effect": "Allow",
                                    "Resource": f"arn:aws:cloudformation:*:*:stack/{stack_name}/*",
                                },
                            ],
                        },
                    ),
                )

    def update_conduit_stack_resources(
        self,
        application_name: str,
        env: str,
        addon_type: str,
        addon_name: str,
        task_name: str,
        parameter_name: str,
        access: str,
    ):
        conduit_stack_name = f"task-{task_name}"
        template = self.cloudformation_client.get_template(StackName=conduit_stack_name)
        template_yml = load_yaml(template["TemplateBody"])

        template_yml["Resources"]["LogGroup"]["DeletionPolicy"] = "Retain"

        template_yml["Resources"]["TaskNameParameter"] = load_yaml(
            f"""
            Type: AWS::SSM::Parameter
            Properties:
              Name: {parameter_name}
              Type: String
              Value: {task_name}
            """
        )

        log_filter_role_arn = self.iam_client.get_role(RoleName="CWLtoSubscriptionFilterRole")[
            "Role"
        ]["Arn"]

        destination_log_group_arns = json.loads(
            self.ssm_client.get_parameter(Name="/copilot/tools/central_log_groups")["Parameter"][
                "Value"
            ]
        )

        destination_arn = destination_log_group_arns["dev"]
        if env.lower() in ("prod", "production"):
            destination_arn = destination_log_group_arns["prod"]

        template_yml["Resources"]["SubscriptionFilter"] = load_yaml(
            f"""
            Type: AWS::Logs::SubscriptionFilter
            DeletionPolicy: Retain
            Properties:
              RoleArn: {log_filter_role_arn}
              LogGroupName: /copilot/{task_name}
              FilterName: /copilot/conduit/{application_name}/{env}/{addon_type}/{addon_name}/{task_name.rsplit("-", 1)[1]}/{access}
              FilterPattern: ''
              DestinationArn: {destination_arn}
            """
        )

        params = []
        if "Parameters" in template_yml:
            for param in template_yml["Parameters"]:
                params.append({"ParameterKey": param, "UsePreviousValue": True})

        self.cloudformation_client.update_stack(
            StackName=conduit_stack_name,
            TemplateBody=dump_yaml(template_yml),
            Parameters=params,
            Capabilities=["CAPABILITY_IAM"],
        )

        return conduit_stack_name

    def wait_for_cloudformation_to_reach_status(self, stack_status, stack_name):
        waiter = self.cloudformation_client.get_waiter(stack_status)

        try:
            waiter.wait(StackName=stack_name, WaiterConfig={"Delay": 5, "MaxAttempts": 20})
        except botocore.exceptions.WaiterError as err:
            current_status = err.last_response.get("Stacks", [{}])[0].get("StackStatus", "")

            if current_status in [
                "ROLLBACK_IN_PROGRESS",
                "UPDATE_ROLLBACK_IN_PROGRESS",
                "ROLLBACK_FAILED",
            ]:
                raise CloudFormationException(stack_name, current_status)
            else:
                raise CloudFormationException(
                    stack_name, f"Error while waiting for stack status: {str(err)}"
                )

    def get_cloudformation_exports_for_environment(self, environment_name):
        exports = []

        for page in self.cloudformation_client.get_paginator("list_exports").paginate():
            for export in page["Exports"]:
                if f"-{environment_name}-" in export["Name"]:
                    exports.append(export)

        return exports


class CloudFormationException(PlatformException):
    def __init__(self, stack_name: str, current_status: str):
        super().__init__(
            f"The CloudFormation stack '{stack_name}' is not in a good state: {current_status}"
        )
