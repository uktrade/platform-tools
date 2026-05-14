import re
from typing import Literal
from typing import Optional

from pydantic import BaseModel
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
    read: bool
    write: bool
    cyber_sign_off_by: str

    @field_validator("cyber_sign_off_by")
    @classmethod
    def valid_cyber_sign_off_by(cls, v: str) -> str:
        if not re.match(r"^[\w.-]+@(businessandtrade\.gov\.uk|digital\.trade\.gov\.uk)$", v):
            raise ValueError("must contain a valid DBT email address")
        return v


class ExternalUserAccess(BaseModel):
    entries: dict[str, ExternalUserAccessEntry]

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
    engine: Optional[str] = None
    deletion_policy: Optional[Literal["Delete", "Retain"]] = None
    plan: Optional[Literal[*plan_manager.get_plan_names("opensearch")]] = None
    volume_size: Optional[int] = None
    ebs_throughput: Optional[int] = None
    ebs_volume_type: Optional[str] = None
    instance: Optional[str] = None
    instances: Optional[int] = None
    master: Optional[bool] = None
    es_app_log_retention_in_days: Optional[int] = None
    index_slow_log_retention_in_days: Optional[int] = None
    audit_log_retention_in_days: Optional[int] = None
    search_slow_log_retention_in_days: Optional[int] = None
    password_special_characters: Optional[str] = None
    urlencode_password: Optional[bool] = None
    external_user_access: Optional[dict[str, ExternalUserAccessEntry]] = None


class OpensearchExtension(BaseModel):

    type: Literal["opensearch"]
    environments: Optional[dict[str, OpenSearch]] = None

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
