import json

import boto3
from moto import mock_aws

from dbt_platform_helper.providers.parameter_store import ParameterStore
from dbt_platform_helper.providers.service import Service, ServiceRepository

MOCK_SERVICE_PARAMS = [
    {
        "Name": f"/platform/applications/my-app/environments/my-env/services/job-1",
        "Value": json.dumps({"name": "job-1", "type": "Scheduled Job"}),
        "Type": 'String',
    },
    {
        "Name": f"/platform/applications/my-app/environments/my-env/services/service-1",
        "Value": json.dumps({"name": "service-1", "type": "Load Balanced Web Service"}),
        "Type": 'String',
    },
    {
        "Name": f"/platform/applications/my-app/environments/my-env/services/backend-1",
        "Value": json.dumps({"name": "backend-1", "type": "Backend Service"}),
        "Type": 'String',
    }
]


@mock_aws
def test_list_services():
    client = boto3.client("ssm", region_name="eu-west-2")
    
    for param in MOCK_SERVICE_PARAMS:
        client.put_parameter(**param)
    
    
    service_repository = ServiceRepository(ParameterStore(client, True))
    services = service_repository.list_services("my-app", "my-env")
    assert len(services) == 3
    # assert Service("job-1","Load Balanced Web Service") in services