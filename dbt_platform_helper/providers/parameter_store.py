import boto3

from dbt_platform_helper.platform_exception import PlatformException


class ParameterStore:
    def __init__(self, ssm_client: boto3.client):
        self.ssm_client = ssm_client

    def get_ssm_parameter_by_name(self, parameter_name: str):
        """Retrieves the latest version of a parameter from parameter store for
        a given name/arn."""

        response = self.ssm_client.get_parameters(Names=[parameter_name])["Parameters"]

        if response:
            return response[0]
        else:
            raise ParameterNotFoundForNameException()

    def get_ssm_parameters_by_path(self, path: str):
        """Retrieves all SSM parameters for a given path from parameter
        store."""

        parameters = []
        paginator = self.ssm_client.get_paginator("get_parameters_by_path")
        page_iterator = paginator.paginate(Path=path, Recursive=True)

        for page in page_iterator:
            parameters.extend(page.get("Parameters", []))

        if parameters:
            return parameters
        else:
            raise ParameterNotFoundForPathException()


class ParameterNotFoundForNameException(PlatformException):
    """Exception raised when a given parameter name cannot be found in SSM."""


class ParameterNotFoundForPathException(PlatformException):
    """Exception raised when no parameters are found for a given path."""
