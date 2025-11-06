from typing import Any

import boto3
from botocore.exceptions import ClientError

from dbt_platform_helper.platform_exception import PlatformException


class AutoscalingProvider:
    def __init__(self, client: boto3.client):
        self.autoscaling_client = client

    def describe_autoscaling_target(
        self, cluster_name: str, ecs_service_name: str
    ) -> dict[str, Any]:
        """Return autoscaling target information for an ECS service."""

        try:
            response = self.autoscaling_client.describe_scalable_targets(
                ServiceNamespace="ecs", ResourceIds=[f"service/{cluster_name}/{ecs_service_name}"]
            )
            return response["ScalableTargets"][0]
        except ClientError as err:
            raise PlatformException(f"Error retrieving scalable targets: {err}")
