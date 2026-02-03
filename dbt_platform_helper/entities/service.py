import re
from enum import Enum
from typing import ClassVar
from typing import Dict
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from dbt_platform_helper.platform_exception import PlatformException


class HealthCheck(BaseModel):
    path: Optional[str] = Field(
        description="The destination that the health check requests are sent to.", default="/"
    )
    port: Optional[int] = Field(
        description="The port that the health check requests are sent to.", default=8080
    )
    success_codes: Optional[str] = Field(
        description="A comma-separated list of HTTP status codes that healthy targets must use when responding to a HTTP health check.",
        default="200",
    )
    healthy_threshold: Optional[int] = Field(
        description="The number of consecutive health check successes required before considering an unhealthy target healthy.",
        default=3,
    )
    unhealthy_threshold: Optional[int] = Field(
        description="The number of consecutive health check failures required before considering a target unhealthy.",
        default=3,
    )
    interval: Optional[int] = Field(
        description="The approximate amount of time, in seconds, between health checks of an individual target.",
        default=35,
    )
    timeout: Optional[int] = Field(
        description="The amount of time, in seconds, during which no response from a target means a failed health check.",
        default=30,
    )
    grace_period: Optional[int] = Field(
        description="The amount of time to ignore failing target group healthchecks on container start.",
        default=30,
    )


class AdditionalRules(BaseModel):
    path: str = Field(description="""Requests to this path will be forwarded to your service.""")
    alias: list[str] = Field(description="""The HTTP domain alias of the service.""")


class Http(BaseModel):
    alias: list[str] = Field(
        description="List of HTTPS domain alias(es) of your service.", default=None
    )
    stickiness: Optional[bool] = Field(description="Enable sticky sessions.", default=False)
    path: str = Field(description="Requests to this path will be forwarded to your service.")
    target_container: str = Field(description="Target container for the requests.")
    healthcheck: HealthCheck = Field(default_factory=HealthCheck)
    additional_rules: Optional[list[AdditionalRules]] = Field(default=None)
    deregistration_delay: Optional[int] = Field(
        default=60,
        description="The amount of time to wait for targets to drain connections during deregistration.",
    )


class HttpOverride(BaseModel):
    alias: Optional[list[str]] = Field(
        description="List of HTTPS domain alias(es) of your service.", default=None
    )
    stickiness: Optional[bool] = Field(description="Enable sticky sessions.", default=None)
    path: Optional[str] = Field(
        description="Requests to this path will be forwarded to your service.", default=None
    )
    target_container: Optional[str] = Field(
        description="Target container for the requests", default=None
    )
    healthcheck: Optional[HealthCheck] = Field(default=None)
    additional_rules: Optional[list[AdditionalRules]] = Field(default=None)
    deregistration_delay: Optional[int] = Field(
        default=None,
        description="The amount of time to wait for targets to drain connections during deregistration.",
    )


class ContainerHealthCheck(BaseModel):
    command: list[str] = Field(
        description="The command to run to determine if the container is healthy."
    )
    interval: Optional[int] = Field(
        default=10, description="Time period between health checks, in seconds."
    )
    retries: Optional[int] = Field(
        default=2, description="Number of times to retry before container is deemed unhealthy."
    )
    timeout: Optional[int] = Field(
        default=5,
        description="How long to wait before considering the health check failed, in seconds.",
    )
    start_period: Optional[int] = Field(
        default=0,
        description="Length of grace period for containers to bootstrap before failed health checks count towards the maximum number of retries.",
    )


class Sidecar(BaseModel):
    port: int = Field(description="Container port exposed by the sidecar to receive traffic.")
    image: str = Field(description="Container image URI for the sidecar (e.g. 'repo/image:tag').")
    essential: Optional[bool] = Field(
        description="Whether the ECS task should stop if this sidecar container exits.",
        default=True,
    )
    variables: Optional[Dict[str, Union[str, int, bool]]] = Field(
        description="Environment variables to inject into the sidecar container.", default=None
    )
    secrets: Optional[Dict[str, str]] = Field(
        description="Parameter Store secrets to inject into the sidecar.", default=None
    )
    healthcheck: Optional[ContainerHealthCheck] = Field(default=None)


class SidecarOverride(BaseModel):
    port: Optional[int] = Field(default=None)
    image: Optional[str] = Field(default=None)
    essential: Optional[bool] = Field(default=None)
    variables: Optional[Dict[str, Union[str, int, bool]]] = Field(default=None)
    secrets: Optional[Dict[str, str]] = Field(default=None)
    healthcheck: Optional[ContainerHealthCheck] = Field(default=None)


class Image(BaseModel):
    location: str = Field(description="Main container image location.")
    port: Optional[int] = Field(
        description="Port exposed by the main ECS task container (used by the load balancer/Service Connect).",
        default=None,
    )
    depends_on: Optional[dict[str, str]] = Field(
        description="Container dependency conditions.", default=None
    )
    healthcheck: Optional[ContainerHealthCheck] = Field(default=None)

    @field_validator("location", mode="after")
    @classmethod
    def is_image_untagged(cls, value: str) -> str:
        image_name = value.split("/")[-1]
        if ":" in image_name:
            raise PlatformException(
                f"Image location cannot contain a tag '{value}'\nPlease remove the tag from your image location. The image tag is automatically added during deployment."
            )
        return value


class Storage(BaseModel):
    readonly_fs: Optional[bool] = Field(
        description="Specify true to give your container read-only access to its root file system.",
        default=False,
    )
    writable_directories: Optional[list[str]] = Field(
        description="List of directories with read/write access.", default=None
    )

    @field_validator("writable_directories", mode="after")
    @classmethod
    def has_leading_forward_slash(cls, value: Union[list, None]) -> Union[list, None]:
        if value is not None:
            for path in value:
                if not path.startswith("/"):
                    raise PlatformException(
                        "All writable directory paths must be absolute (starts with a /)"
                    )
        return value


class Cooldown(BaseModel):
    in_: Optional[int] = Field(
        alias="in",
        description="Number of seconds to wait before scaling in (down) after a drop in load.",
        default=60,
    )  # Can't use 'in' because it's a reserved keyword
    out: Optional[int] = Field(
        description="Number of seconds to wait before scaling out (up) after a spike in load.",
        default=60,
    )

    @field_validator("in_", "out", mode="before")
    @classmethod
    def parse_seconds(cls, value):
        if isinstance(value, str) and value.endswith("s"):
            value = value.removesuffix("s")  # remove the trailing 's'
        try:
            return int(value)
        except (ValueError, TypeError):
            raise PlatformException("Cooldown values must be integers or strings like '30s'")


class CpuPercentage(BaseModel):
    value: int = Field(description="Target CPU utilisation percentage that triggers autoscaling.")
    cooldown: Optional[Cooldown] = Field(
        default=None, description="Optional CPU cooldown that overrides the global cooldown policy."
    )


class MemoryPercentage(BaseModel):
    value: int = Field(description="Target CPU utilisation percentage that triggers autoscaling.")
    cooldown: Optional[Cooldown] = Field(
        default=None,
        description="Optional memory cooldown that overrides the global cooldown policy.",
    )


class RequestsPerMinute(BaseModel):
    value: int = Field(
        description="Number of incoming requests per minute that triggers autoscaling."
    )
    cooldown: Optional[Cooldown] = Field(
        default=None,
        description="Optional requests cooldown that overrides the global cooldown policy.",
    )


class Count(BaseModel):
    range: str = Field(
        description="Minimum and maximum number of ECS tasks to maintain e.g. '1-2'."
    )
    cooldown: Optional[Cooldown] = Field(
        default=None,
        description="Global cooldown applied to all autoscaling metrics unless overridden per metric.",
    )
    cpu_percentage: Optional[Union[int, CpuPercentage]] = Field(
        default=None,
        description="CPU utilisation threshold (0–100). Either a plain integer or a map with 'value' and 'cooldown'.",
    )
    memory_percentage: Optional[Union[int, MemoryPercentage]] = Field(
        default=None,
        description="Memory utilisation threshold (0–100). Either a plain integer or a map with 'value' and 'cooldown'.",
    )
    requests_per_minute: Optional[Union[int, RequestsPerMinute]] = Field(
        default=None,
        description="Request-rate threshold. Either a plain integer or a map with 'value' and 'cooldown'.",
    )

    @model_validator(mode="after")
    def at_least_one_autoscaling_metric(self):

        if not any([self.cpu_percentage, self.memory_percentage, self.requests_per_minute]):
            raise PlatformException(
                "If autoscaling is enabled, you must define at least one metric: "
                "cpu_percentage, memory_percentage, or requests_per_minute"
            )

        if not re.match(r"^(\d+)-(\d+)$", self.range):
            raise PlatformException("Range must be in the format 'int-int' e.g. '1-2'")

        range_split = self.range.split("-")
        if int(range_split[0]) >= int(range_split[1]):
            raise PlatformException("Range minimum value must be less than the maximum value.")

        return self


class ServiceConfigEnvironmentOverride(BaseModel):
    http: Optional[HttpOverride] = Field(default=None)
    sidecars: Optional[Dict[str, SidecarOverride]] = Field(default=None)
    image: Optional[Image] = Field(default=None)

    cpu: Optional[int] = Field(default=None)
    memory: Optional[int] = Field(default=None)
    count: Optional[Union[int, Count]] = Field(default=None)
    exec: Optional[bool] = Field(default=None)
    entrypoint: Optional[list[str]] = Field(default=None)
    essential: Optional[bool] = Field(default=None)

    storage: Optional[Storage] = Field(default=None)

    variables: Optional[Dict[str, Union[str, int, bool]]] = Field(default=None)
    secrets: Optional[Dict[str, str]] = Field(default=None)


class ServiceType(str, Enum):
    BACKEND_SERVICE = "Backend Service"
    LOAD_BALANCED_WEB_SERVICE = "Load Balanced Web Service"


class ServiceConfig(BaseModel):
    name: str = Field(description="Service name.")
    type: ServiceType = Field(
        description=f"Type of service. Must one one of: '{ServiceType.LOAD_BALANCED_WEB_SERVICE.value}', '{ServiceType.BACKEND_SERVICE.value}'"
    )
    http: Optional[Http] = Field(default=None)

    @model_validator(mode="after")
    def check_http_for_web_service(self):
        if self.type == ServiceType.LOAD_BALANCED_WEB_SERVICE and self.http is None:
            raise PlatformException(
                f"A 'http' block must be provided when service type == {self.type.value}"
            )
        return self

    sidecars: Optional[Dict[str, Sidecar]] = Field(default=None)
    image: Image = Field()
    cpu: int = Field(
        description="vCPU units reserved for the ECS task (e.g. 256=0.25 vCPU, 512=0.5 vCPU, 1024=1 vCPU)."
    )
    memory: int = Field(
        description="Memory in MiB reserved for the ECS task (e.g. 256, 512, 1024)."
    )
    count: Union[int, Count] = Field(
        description="Desired task count — either a fixed integer or an autoscaling policy map with 'range', 'cooldown', and at least one of 'cpu_percentage', 'memory_percentage', or 'requests_per_minute' metrics."
    )
    exec: Optional[bool] = Field(
        description="Enable ECS Exec (remote command execution) for running ECS tasks.",
        default=False,
    )
    entrypoint: Optional[list[str]] = Field(
        description="Overrides the default entrypoint in the image.", default=None
    )
    essential: Optional[bool] = Field(
        description="Whether the main container is marked essential; The entire ECS task stops if it exits.",
        default=True,
    )
    storage: Storage = Field(default_factory=Storage)
    variables: Optional[Dict[str, Union[str, int, bool]]] = Field(
        description="Environment variables to inject into the main application container.",
        default=None,
    )
    secrets: Optional[Dict[str, str]] = Field(
        description="Parameter Store secrets to inject into the main application container.",
        default=None,
    )
    # Environment overrides can override almost the full config
    environments: Optional[Dict[str, ServiceConfigEnvironmentOverride]] = Field(
        description="Allows you to override most service config properties for specific environments.",
        default=None,
    )

    # Class based variable used when handling the object
    local_terraform_source: ClassVar[str] = "../../../../../platform-tools/terraform/ecs-service"
