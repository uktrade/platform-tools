import boto3

from dbt_platform_helper.platform_exception import PlatformException


class ParameterStore:
    def __init__(self, ssm_client: boto3.client):
        self.ssm_client = ssm_client

    def get_ssm_parameter_by_name(self, parameter_name: str) -> dict:
        """
        Retrieves the latest version of a parameter from parameter store for a
        given name/arn.

        Args:
            path (str): The parameter name to retrieve the parameter value for.
        Returns:
            dict: A dictionary representation of your ssm parameter
        """

        return self.ssm_client.get_parameter(Name=parameter_name)["Parameter"]

    def get_ssm_parameters_by_path(self, path: str) -> list:
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


class ParameterNotFoundForPathException(PlatformException):
    """Exception raised when no parameters are found for a given path."""
