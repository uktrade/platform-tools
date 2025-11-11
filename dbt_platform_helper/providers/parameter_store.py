from dataclasses import dataclass
from typing import Literal
from typing import Union

import boto3

from dbt_platform_helper.platform_exception import PlatformException


@dataclass
class Parameter:

    name: str
    value: str
    arn: str = None
    data_type: Literal["text", "aws:ec2:image"] = "text"
    param_type: Literal["String", "StringList", "SecureString"] = (
        "SecureString"  # Returned as 'Type' from AWS
    )
    version: int = None
    # tags: list = []

    def __str__(self):
        output = f"Application {self.name} with"

        return f"{output} no environments"

    def __eq__(self, other: "Parameter"):
        return str(self.name) == str(other.name)


class ParameterStore:
    def __init__(self, ssm_client: boto3.client, with_model: bool = False):
        self.ssm_client = ssm_client
        self.with_model = with_model

    def get_ssm_parameter_by_name(self, parameter_name: str) -> Union[dict | Parameter]:
        """
        Retrieves the latest version of a parameter from parameter store for a
        given name/arn.

        Args:
            path (str): The parameter name to retrieve the parameter value for.
        Returns:
            dict: A dictionary representation of your ssm parameter
        """
        parameter = self.ssm_client.get_parameter(Name=parameter_name)["Parameter"]
        if self.with_model:
            parameter = Parameter()
        return parameter

    def get_ssm_parameters_by_path(self, path: str, add_tags=False) -> list:
        """
        Retrieves all SSM parameters for a given path from parameter store.

        Args:
            path (str): The parameter path to retrieve the parameters for. e.g. /copilot/applications/
        Returns:
            list: A list of dictionaries containing all SSM parameters under the provided path.
        """

        parameters = []
        paginator = self.ssm_client.get_paginator("get_parameters_by_path")
        page_iterator = paginator.paginate(Path=path, Recursive=True)

        for page in page_iterator:
            parameters.extend(page.get("Parameters", []))

        if parameters:
            return parameters
        else:
            raise ParameterNotFoundForPathException()

    def put_parameter(self, data_dict: dict) -> dict:
        return self.ssm_client.put_parameter(**data_dict)


class ParameterNotFoundForPathException(PlatformException):
    """Exception raised when no parameters are found for a given path."""
