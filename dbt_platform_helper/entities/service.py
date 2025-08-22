from typing import ClassVar
from typing import Dict
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import Field


class HealthCheck(BaseModel):
    path: Optional[str] = Field(description="""Path the healthcheck calls""", default=None)
    port: Optional[int] = Field(description="""Port the healthcheck calls""", default=None)
    success_codes: Optional[str] = Field(
        description="""The success codes the healthcheck looks for""", default=None
    )
    healthy_threshold: Optional[int] = Field(description="""The number of  """, default=None)
    unhealthy_threshold: Optional[int] = Field(description="""The number of """, default=None)
    interval: Optional[str] = Field(
        description="""The interval inbetween health check calls""", default=None
    )
    timeout: Optional[str] = Field(
        description="""The timeout for a healthcheck call""", default=None
    )
    grace_period: Optional[str] = Field(description="""The time""", default=None)


class Http(BaseModel):
    path: Optional[str] = Field(
        description="""Requests to this path will be forwarded to your service.""", default=None
    )
    alb: Optional[str] = Field(default=None)
    target_container: Optional[str] = Field(
        description="""Target container for the requests""", default=None
    )
    healthcheck: Optional[HealthCheck] = Field(default=None)


class Sidecar(BaseModel):
    port: int = Field()
    image: str = Field()
    essential: Optional[bool] = Field(default=None)
    variables: Optional[Dict[str, Union[str, int, bool]]] = Field(default=None)
    secrets: Optional[Dict[str, str]] = Field(default=None)


class SidecarOverride(BaseModel):
    port: Optional[int] = Field(default=None)
    image: Optional[str] = Field(default=None)
    essential: Optional[bool] = Field(default=None)
    variables: Optional[Dict[str, Union[str, int, bool]]] = Field(default=None)
    secrets: Optional[Dict[str, str]] = Field(default=None)


class Image(BaseModel):
    build: Optional[str] = Field(default=None)
    location: Optional[str] = Field(default=None)
    port: Optional[int] = Field(default=None)


class VPC(BaseModel):
    placement: str = Field()


class Network(BaseModel):
    connect: bool = Field(
        description="Enable Service Connect for intra-environment traffic between services."
    )
    vpc: Optional[VPC] = Field(default=None)


class Storage(BaseModel):
    readonly_fs: bool


class ServiceConfigEnvironmentOverride(BaseModel):
    http: Optional[Http] = Field(default=None)
    sidecars: Optional[Dict[str, SidecarOverride]] = Field(default=None)
    image: Optional[Image] = Field(default=None)

    cpu: Optional[int] = Field(default=None)
    memory: Optional[int] = Field(default=None)
    count: Optional[int] = Field(default=None)
    exec: Optional[bool] = Field(default=None)
    network: Optional[Network] = Field(default=None)

    storage: Optional[Storage] = Field(default=None)

    variables: Optional[Dict[str, Union[str, int, bool]]] = Field(default=None)
    secrets: Optional[Dict[str, str]] = Field(default=None)


class ServiceConfig(BaseModel):
    name: str = Field(description="""Name of the Service.""")
    type: str = Field(description="""The type of service""")

    http: Optional[Http] = Field(default=None)  # TODO http required if service type load balancer
    sidecars: Optional[Dict[str, Sidecar]] = Field(default=None)
    image: Image = Field()

    cpu: int = Field()
    memory: int = Field()
    count: int = Field()
    exec: Optional[bool] = Field(default=None)
    network: Optional[Network] = Field(default=None)

    storage: Optional[Storage] = Field(default=None)

    variables: Optional[Dict[str, Union[str, int, bool]]] = Field(default=None)
    secrets: Optional[Dict[str, str]] = Field(default=None)
    # Environment overrides can override almost the full config
    environments: Optional[Dict[str, ServiceConfigEnvironmentOverride]] = Field(default=None)

    # Class based variable used when handling the obejct
    local_terraform_source: ClassVar[str] = "../../../../../platform-tools/terraform/ecs-service"
