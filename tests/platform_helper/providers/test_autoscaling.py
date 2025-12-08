from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.autoscaling import AutoscalingProvider


def test_describe_scalable_targets_success():
    autoscaling_client = MagicMock()
    autoscaling_client.describe_scalable_targets.return_value = {
        "ScalableTargets": [{"ServiceNamespace": "ecs", "MaxCapacity": 1}]
    }

    autoscaling = AutoscalingProvider(autoscaling_client)
    response = autoscaling.describe_autoscaling_target(
        cluster_name="myapp-dev-cluster", ecs_service_name="myapp-dev-web"
    )

    assert response == {"ServiceNamespace": "ecs", "MaxCapacity": 1}
    autoscaling_client.describe_scalable_targets.assert_called_once_with(
        ServiceNamespace="ecs", ResourceIds=["service/myapp-dev-cluster/myapp-dev-web"]
    )


def test_describe_scalable_targets_raises_exception():
    autoscaling_client = MagicMock()
    autoscaling_client.describe_scalable_targets.side_effect = ClientError(
        {"Error": {"Code": "InternalServiceException", "Message": ""}}, "DescribeScalableTargets"
    )

    provider = AutoscalingProvider(client=autoscaling_client)

    with pytest.raises(PlatformException) as e:
        provider.describe_autoscaling_target(
            cluster_name="myapp-dev-cluster", ecs_service_name="myapp-dev-web"
        )

    assert "Error retrieving scalable targets" in str(e.value)
