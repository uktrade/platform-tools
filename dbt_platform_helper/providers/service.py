import json
from dataclasses import dataclass

from dbt_platform_helper.entities.service import ServiceType
from dbt_platform_helper.providers.parameter_store import ParameterStore
from dbt_platform_helper.utils.application import Service


class ServiceRepository:

    def __init__(self, parameter_store: ParameterStore):
        self.parameter_store = parameter_store

    def list_services(self, app, env, type: ServiceType = None):
        service_parameters = self.parameter_store.get_ssm_parameters_by_path(
            f"/platform/applications/{app}/environments/{env}/services/"
        )
        services = []
        for param in service_parameters:
            value = json.loads(param.value)
            if type:
                if value.get("type") == "Scheduled Job":
                    services.append(Service(value.get("name"), type))
            else:
                services.append(Service(value.get("name"), value.get("type")))
        return services

    def list_jobs(self, app, env):
        return self.list_services(app, env, ServiceType("Scheduled Job"))
