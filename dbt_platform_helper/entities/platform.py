import re
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator
from schema import SchemaError

from dbt_platform_helper.domain.plans import PlanLoader

plan_manager = PlanLoader()
plan_manager.load()

OPENSEARCH_MAX_VOLUME_SIZE: dict[str, int] = {
    "tiny": 100,
    "small": 200,
    "small-ha": 200,
    "medium": 512,
    "medium-ha": 512,
    "large": 1000,
    "large-ha": 1000,
    "x-large": 1500,
    "x-large-ha": 1500,
}
OPENSEARCH_MIN_VOLUME_SIZE = 10


class ExternalUserAccessEntry(BaseModel):
    index: bool = Field(description="Enable index access for the user.")
    read: bool = Field(description="Enable read access for the user.")
    write: bool = Field(description="Enable write access for the user.")
    cyber_sign_off_by: str = Field(
        description="The DBT email address of the cybersecurity team member that signed off the access."
    )

    @field_validator("cyber_sign_off_by")
    @classmethod
    def valid_cyber_sign_off_by(cls, v: str) -> str:
        if not re.match(r"^[\w.-]+@(businessandtrade\.gov\.uk|digital\.trade\.gov\.uk)$", v):
            raise ValueError("must be a valid DBT email address")
        return v


class ExternalUserAccess(BaseModel):
    entries: dict[str, ExternalUserAccessEntry] = Field(
        description='For the key, use a descriptive name. Letters, numbers, hyphens and underscores are allowed. E.g. "some-3rd-party-write-user".'
    )

    @field_validator("entries")
    @classmethod
    def validate_keys(cls, v: dict) -> dict:
        import re

        for key in v:

            if not re.match(r"^([a-z][a-zA-Z0-9_-]*)", key):
                raise ValueError(
                    f"Key '{key}' is invalid: must start with lowercase letter,"
                    "only alphanumeric, hyphen, underscore allowed"
                )
        return v


class OpenSearch(BaseModel):
    engine: Optional[str] = Field(
        default=None, description="""The version of OpenSearch. E.g. "2.11"."""
    )
    deletion_policy: Optional[Literal["Delete", "Retain"]] = Field(
        default=None, description="DEPRECATED"
    )
    plan: Optional[str] = (
        Field(  # TODO once python 3.10 is out of support - change str to Literal[*plan_manager.get_plan_names("opensearch")
            default=None,
            description="""For convenience, can be used to apply sensible settings for volume size, number of instances etc.""",
        )
    )
    volume_size: Optional[int] = Field(
        default=None,
        description="""Override the size of EBS volumes attached to the cluster in GiB. This will usually come from the plan used.""",
    )
    ebs_throughput: Optional[int] = Field(
        default=None,
        description="""Throughput in MiB/s. Relevant if ebs_volume_type is "gp3". Defaults to "250".""",
    )
    ebs_volume_type: Optional[str] = Field(
        default=None,
        description="""Type of EBS volumes attached to data nodes. Defaults to "gp2".""",
    )
    instance: Optional[str] = Field(
        default=None,
        description="""Override the instance type of data nodes in the cluster. This will usually come from the plan used.""",
    )
    instances: Optional[int] = Field(
        default=None, description="""The number of instances in the cluster. Defaults to "1"."""
    )
    master: Optional[bool] = Field(default=None, description="DEPRECATED")
    es_app_log_retention_in_days: Optional[int] = Field(
        default=None,
        description="""The number of days you want to retain audit log events. Possible values are: 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653, and 0. If you select 0, the events in the log group are always retained and never expire. Defaults to "7".""",
    )
    index_slow_log_retention_in_days: Optional[int] = Field(
        default=None,
        description="""The number of days you want to retain audit log events. Possible values are: 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653, and 0. If you select 0, the events in the log group are always retained and never expire. Defaults to "7".""",
    )
    audit_log_retention_in_days: Optional[int] = Field(
        default=None,
        description="""The number of days you want to retain audit log events. Possible values are: 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653, and 0. If you select 0, the events in the log group are always retained and never expire. Defaults to "7".""",
    )
    search_slow_log_retention_in_days: Optional[int] = Field(
        default=None,
        description="""The number of days you want to retain audit log events. Possible values are: 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653, and 0. If you select 0, the events in the log group are always retained and never expire. Defaults to "7".""",
    )
    password_special_characters: Optional[str] = Field(
        default=None,
        description="""Use to override the special characters allowed in passwords. Defaults to "-_!.~$&'()*+,;=".""",
    )
    urlencode_password: Optional[bool] = Field(
        default=None,
        description="""Control whether passwords are URL encoded. Defaults to "true".""",
    )
    external_user_access: Optional[dict[str, ExternalUserAccessEntry]] = Field(
        default=None,
        description="""Allow extra Users to be defined to be used for access from outwith the account.""",
    )

    # Explicit validator as pythonn 3.10 does not support dyanmically setting Literals in the type Annotations
    @field_validator("plan")
    @classmethod
    def validate_plan_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed_plans = plan_manager.get_plan_names("opensearch")
        if v not in allowed_plans:
            raise ValueError(f"Plan must be one of {allowed_plans}")
        return v

    @field_validator("external_user_access")
    @classmethod
    def validate_keys(cls, v: dict) -> dict:
        import re

        for key in v:

            if not re.match(r"^([a-z][a-zA-Z0-9_-]*)", key):
                raise ValueError(
                    f"Key '{key}' is invalid: must start with lowercase letter,"
                    "only alphanumeric, hyphen, underscore allowed"
                )
        return v


class OpensearchExtension(BaseModel):

    type: Literal["opensearch"] = Field(description="""Use "opensearch".""")
    environments: Optional[dict[str, OpenSearch]] = Field(
        default=None, description="""The OpenSearch configurations for your environments."""
    )

    @model_validator(mode="after")
    def validate_volume_size(self):
        """Validate volume_size constraints based on plan."""

        if not self.environments:
            return self

        default_env_config = self.environments.get("*") or self.environments.get("default")

        default_plan = default_env_config.plan if default_env_config else None
        default_volume_size = default_env_config.volume_size if default_env_config else None

        for env, env_config in self.environments.items():
            plan = env_config.plan or default_plan
            volume_size = env_config.volume_size or default_volume_size

            if volume_size is None:
                continue

            if not plan:
                raise ValueError("Missing key: 'plan'")

            if volume_size < OPENSEARCH_MIN_VOLUME_SIZE:
                raise ValueError(
                    f"Key 'environments' error: Key '{env}' error: Key 'volume_size' error: should be an integer greater than {OPENSEARCH_MIN_VOLUME_SIZE}"
                )

            max_size = OPENSEARCH_MAX_VOLUME_SIZE.get(plan)
            if max_size and volume_size > max_size:
                raise ValueError(
                    f"Key 'environments' error: Key '{env}' error: Key 'volume_size' error: should be an integer between {OPENSEARCH_MIN_VOLUME_SIZE} and {max_size} for plan {plan}"
                )
        return self


# Factories
class OpensearchExtensionSchema:
    """Temp class to integrate pydantic into platform config."""

    def validate(self, raw: dict) -> dict:
        from pydantic import ValidationError

        try:
            OpensearchExtension.model_validate(raw)
        except ValidationError as e:
            raise SchemaError(str(e))
        return raw

    def __call__(self, raw):
        return self.validate(raw)


# for schema integration for now, when fully pydantic not required
def external_user_access_validator(raw: dict) -> dict:
    from pydantic import ValidationError

    try:
        ExternalUserAccess(entries=raw)
    except ValidationError as e:
        raise SchemaError(str(e))

    return raw


def validate_extension_fn(extension):

    def validate_extension(raw):
        from pydantic import ValidationError

        try:
            if extension == "opensearch":
                OpensearchExtension.model_validate(raw)
        except ValidationError as e:
            raise SchemaError(str(e))
        return raw

    return validate_extension
