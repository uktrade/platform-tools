import json

import boto3
import pytest
from moto import mock_aws

from dbt_platform_helper.entities.service import ServiceType
from dbt_platform_helper.providers.parameter_store import ParameterStore
from dbt_platform_helper.providers.service import Service
from dbt_platform_helper.providers.service import ServiceRepository

MOCK_SERVICE_PARAMS = [
    {
        "Name": f"/platform/applications/my-app/environments/my-env/services/job-1",
        "Value": json.dumps({"name": "job-1", "type": "Scheduled Job"}),
        "Type": "String",
    },
    {
        "Name": f"/platform/applications/my-app/environments/my-env/services/service-1",
        "Value": json.dumps({"name": "service-1", "type": "Load Balanced Web Service"}),
        "Type": "String",
    },
    {
        "Name": f"/platform/applications/my-app/environments/my-env/services/backend-1",
        "Value": json.dumps({"name": "backend-1", "type": "Backend Service"}),
        "Type": "String",
    },
]


@mock_aws
def test_list_services():
    client = boto3.client("ssm", region_name="eu-west-2")

    for param in MOCK_SERVICE_PARAMS:
        client.put_parameter(**param)

    service_repository = ServiceRepository(ParameterStore(client, True))
    services = service_repository.list_services("my-app", "my-env")
    assert len(services) == 3
    assert Service("job-1", "Scheduled Job") in services
    assert Service("service-1", "Load Balanced Web Service") in services
    assert Service("backend-1", "Backend Service") in services


@mock_aws
def test_list_services_given_no_matching_parameters():
    client = boto3.client("ssm", region_name="eu-west-2")

    for param in MOCK_SERVICE_PARAMS:
        client.put_parameter(**param)

    service_repository = ServiceRepository(ParameterStore(client, True))
    services = service_repository.list_services("my-other-app", "my-env")
    assert len(services) == 0


@pytest.mark.parametrize(
    "type",
    [
        "Scheduled Job",
        "Load Balanced Web Service",
        "Backend Service",
    ],
)
@mock_aws
def test_list_services_by_type(type):
    client = boto3.client("ssm", region_name="eu-west-2")

    for param in MOCK_SERVICE_PARAMS:
        client.put_parameter(**param)

    service_repository = ServiceRepository(ParameterStore(client, True))
    service_type = ServiceType(type)
    services = service_repository.list_services("my-app", "my-env", service_type)
    assert len(services) == 1
    assert services[0].kind == type


@mock_aws
def test_list_jobs():
    client = boto3.client("ssm", region_name="eu-west-2")

    for param in MOCK_SERVICE_PARAMS:
        client.put_parameter(**param)

    service_repository = ServiceRepository(ParameterStore(client, True))
    services = service_repository.list_jobs("my-app", "my-env")
    assert len(services) == 1
    assert Service("job-1", "Scheduled Job") in services


@mock_aws
def test_list_jobs_given_empty_parameter_store():
    client = boto3.client("ssm", region_name="eu-west-2")

    service_repository = ServiceRepository(ParameterStore(client, True))
    services = service_repository.list_jobs("my-app", "my-env")
    assert len(services) == 0
