from dataclasses import dataclass
from dataclasses import field
from typing import Literal
from typing import Optional
from typing import Union

import boto3

from dbt_platform_helper.platform_exception import PlatformException


@dataclass
class Parameter:

    name: str
    value: str
    arn: str = None
    data_type: Literal["text", "aws:ec2:image"] = "text"
    type: Literal["String", "StringList", "SecureString"] = (
        "SecureString"  # Returned as 'Type' from AWS
    )
    version: int = None
    tags: Optional[dict[str, str]] = field(default_factory=dict)

    def tags_to_list(self):
        return [{"Key": tag, "Value": value} for tag, value in self.tags.items()]

    def __str__(self):
        output = f"Application {self.name} with"

        return f"{output} no environments"

    def __eq__(self, other: "Parameter"):
        return str(self.name) == str(other.name)


class ParameterStore:
    def __init__(self, ssm_client: boto3.client, with_model: bool = False):
        self.ssm_client = ssm_client
        self.with_model = with_model

    def __fetch_tags(self, parameter: Parameter, normalise=True):
        response = self.ssm_client.list_tags_for_resource(
            ResourceType="Parameter", ResourceId=parameter.name
        )["TagList"]

        if normalise:
            return {tag["Key"]: tag["Value"] for tag in response}
        else:
            return response

    def get_ssm_parameter_by_name(
        self, parameter_name: str, add_tags: bool = False
    ) -> Union[dict, Parameter]:
        """
        Retrieves the latest version of a parameter from parameter store for a
        given name/arn.

        Args:
            parameter_name (str): The parameter name to retrieve the parameter value for.
            add_tags (bool): Whether to retrieve the tags for the SSM parameters requested
        Returns:
            dict: A dictionary representation of your ssm parameter
        """
        parameter = self.ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)[
            "Parameter"
        ]

        if not self.with_model:
            return parameter

        model = Parameter(
            name=parameter["Name"],
            value=parameter["Value"],
            arn=parameter["ARN"],
            data_type=parameter["DataType"],
            type=parameter["Type"],
            version=parameter["Version"],
        )

        if add_tags:
            model.tags = self.__fetch_tags(model)

        return model

    def get_ssm_parameters_by_path(
        self, path: str, add_tags: bool = False
    ) -> Union[list[dict], list[Parameter]]:
        """
        Retrieves all SSM parameters for a given path from parameter store.

        Args:
            path (str): The parameter path to retrieve the parameters for. e.g. /copilot/applications/
            add_tags (bool): Whether to retrieve the tags for the SSM parameters requested
        Returns:
            list: A list of dictionaries containing all SSM parameters under the provided path.
        """

        parameters = []
        paginator = self.ssm_client.get_paginator("get_parameters_by_path")
        page_iterator = paginator.paginate(Path=path, Recursive=True, WithDecryption=True)

        for page in page_iterator:
            parameters.extend(page.get("Parameters", []))

        if not self.with_model:
            if parameters:
                return parameters
            else:
                raise ParameterNotFoundForPathException()

        to_model = lambda parameter: Parameter(
            name=parameter["Name"],
            value=parameter["Value"],
            arn=parameter["ARN"],
            data_type=parameter["DataType"],
            type=parameter["Type"],
            version=parameter["Version"],
        )

        models = [to_model(param) for param in parameters]

        if add_tags:
            for model in models:
                model.tags = self.__fetch_tags(model)

        return models

    def put_parameter(self, data_dict: dict) -> dict:
        return self.ssm_client.put_parameter(**data_dict)


class ParameterNotFoundForPathException(PlatformException):
    """Exception raised when no parameters are found for a given path."""
