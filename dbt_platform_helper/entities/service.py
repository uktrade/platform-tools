import re
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
    grace_period: Optional[str] = Field(
        description="""The time the service ignores unhealthy ALB and container health checks""",
        default=None,
    )


class AdditionalRules(BaseModel):
    path: str = Field(description="""Requests to this path will be forwarded to your service.""")
    alias: Union[str, list] = Field(description="""The HTTP domain alias of the service.""")


class Http(BaseModel):
    path: str = Field(description="""Requests to this path will be forwarded to your service.""")
    target_container: str = Field(description="""Target container for the requests""")
    healthcheck: Optional[HealthCheck] = Field(default=None)
    alias: Union[str, list] = Field(description="""The HTTP domain alias of the service.""")
    additional_rules: Optional[list[AdditionalRules]] = Field(default=None)


class HttpOverride(BaseModel):
    path: Optional[str] = Field(
        description="""Requests to this path will be forwarded to your service.""", default=None
    )
    target_container: Optional[str] = Field(
        description="""Target container for the requests""", default=None
    )
    healthcheck: Optional[HealthCheck] = Field(default=None)
    alias: Optional[Union[str, list]] = Field(
        description="""The HTTP domain alias of the service."""
    )
    additional_rules: Optional[list[AdditionalRules]] = Field(default=None)


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
    location: str = Field()
    port: Optional[int] = Field(default=None)
    depends_on: Optional[dict[str, str]] = Field(default=None)


class VPC(BaseModel):
    placement: Optional[str] = Field(default=None)


class Network(BaseModel):
    connect: Optional[bool] = Field(
        description="Enable Service Connect for intra-environment traffic between services.",
        default=None,
    )
    vpc: Optional[VPC] = Field(default=None)


class Storage(BaseModel):
    readonly_fs: Optional[bool] = Field(default=None)
    writable_directories: Optional[list[str]] = Field(default=None)

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
    in_: int = Field(
        alias="in",
        description="Number of seconds to wait before scaling in (down) after a drop in load.",
    )  # Can't use 'in' because it's a reserved keyword
    out: int = Field(
        description="Number of seconds to wait before scaling out (up) after a spike in load."
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
        if range_split[0] >= range_split[1]:
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
    network: Optional[Network] = Field(default=None)

    storage: Optional[Storage] = Field(default=None)

    variables: Optional[Dict[str, Union[str, int, bool]]] = Field(default=None)
    secrets: Optional[Dict[str, str]] = Field(default=None)


class ServiceConfig(BaseModel):
    name: str = Field(description="""Name of the Service.""")
    type: str = Field(description="""The type of service""")

    http: Optional[Http] = Field(default=None)

    @model_validator(mode="after")
    def check_http_for_web_service(self):
        if self.type == "Load Balanced Web Service" and self.http is None:
            raise PlatformException(
                "A 'http' block must be provided when service type == 'Load Balanced Web Service'"
            )
        return self

    sidecars: Optional[Dict[str, Sidecar]] = Field(default=None)
    image: Image = Field()

    cpu: int = Field()
    memory: int = Field()
    count: Union[int, Count] = Field(
        description="Desired task count — either a fixed integer or an autoscaling policy map with 'range', 'cooldown', and at least one of 'cpu_percentage', 'memory_percentage', or 'requests_per_minute' metrics."
    )
    exec: Optional[bool] = Field(default=None)
    entrypoint: Optional[list[str]] = Field(default=None)
    essential: Optional[bool] = Field(default=None)
    network: Optional[Network] = Field(default=None)

    storage: Optional[Storage] = Field(default=None)

    variables: Optional[Dict[str, Union[str, int, bool]]] = Field(default=None)
    secrets: Optional[Dict[str, str]] = Field(default=None)
    # Environment overrides can override almost the full config
    environments: Optional[Dict[str, ServiceConfigEnvironmentOverride]] = Field(default=None)

    # Class based variable used when handling the object
    local_terraform_source: ClassVar[str] = "../../../../../platform-tools/terraform/ecs-service"
