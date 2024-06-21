import ipaddress
import re

import click
from botocore.exceptions import ClientError
from schema import Optional
from schema import Or
from schema import Regex
from schema import Schema
from schema import SchemaError

from dbt_platform_helper.utils.aws import get_aws_session_or_abort


def validate_string(regex_pattern: str):
    def validator(string):
        if not re.match(regex_pattern, string):
            raise SchemaError(
                f"String '{string}' does not match the required pattern '{regex_pattern}'. For more details on valid string patterns see: https://aws.github.io/copilot-cli/docs/manifest/lb-web-service/"
            )
        return string

    return validator


S3_BUCKET_NAME_ERROR_TEMPLATE = "Bucket name '{}' is invalid:\n{}"
AVAILABILITY_UNCERTAIN_TEMPLATE = (
    "Warning: Could not determine the availability of bucket name '{}'."
)
BUCKET_NAME_IN_USE_TEMPLATE = "Warning: Bucket name '{}' is already in use. Check your AWS accounts to see if this is a problem."


def warn_on_s3_bucket_name_availability(name: str):
    """
    We try to find the bucket name in AWS.

    The validation logic is:
    True: if the response is a 200 (it exists and you have access - this bucket has probably already been deployed)
    True: if the response is a 404 (it could not be found)
    False: if the response is 40x (the bucket exists but you have no permission)
    """
    session = get_aws_session_or_abort()
    client = session.client("s3")
    try:
        client.head_bucket(Bucket=name)
        return
    except ClientError as ex:
        if "Error" not in ex.response or not "Code" in ex.response["Error"]:
            click.secho(AVAILABILITY_UNCERTAIN_TEMPLATE.format(name), fg="yellow")
            return
        if ex.response["Error"]["Code"] == "404":
            return
        if int(ex.response["Error"]["Code"]) > 499:
            click.secho(AVAILABILITY_UNCERTAIN_TEMPLATE.format(name), fg="yellow")
            return

    click.secho(BUCKET_NAME_IN_USE_TEMPLATE.format(name), fg="yellow")


def validate_s3_bucket_name(name: str):
    errors = []
    if not (2 < len(name) < 64):
        errors.append("Length must be between 3 and 63 characters inclusive.")

    if not re.match(r"^[a-z0-9].*[a-z0-9]$", name):
        errors.append("Names must start and end with 0-9 or a-z.")

    if not re.match(r"^[a-z0-9.-]*$", name):
        errors.append("Names can only contain the characters 0-9, a-z, '.' and '-'.")

    if ".." in name:
        errors.append("Names cannot contain two adjacent periods.")

    try:
        ipaddress.ip_address(name)
        errors.append("Names cannot be IP addresses.")
    except ValueError:
        pass

    for prefix in ("xn--", "sthree-"):
        if name.startswith(prefix):
            errors.append(f"Names cannot be prefixed '{prefix}'.")

    for suffix in ("-s3alias", "--ol-s3"):
        if name.endswith(suffix):
            errors.append(f"Names cannot be suffixed '{suffix}'.")

    if not errors:
        # Don't waste time calling AWS if the bucket name is not even valid.
        warn_on_s3_bucket_name_availability(name)

    if errors:
        raise SchemaError(
            S3_BUCKET_NAME_ERROR_TEMPLATE.format(name, "\n".join(f"  {e}" for e in errors))
        )

    return True


def validate_addons(addons: dict):
    """
    Validate the addons file and return a dictionary of addon: error message.
    """
    errors = {}

    for addon_name, addon in addons.items():
        try:
            addon_type = addon.get("type", None)
            if not addon_type:
                errors[addon_name] = f"Missing addon type in addon '{addon_name}'"
                continue
            schema = SCHEMA_MAP.get(addon_type, None)
            if not schema:
                errors[addon_name] = (
                    f"Unsupported addon type '{addon_type}' in addon '{addon_name}'"
                )
                continue
            schema.validate(addon)
        except SchemaError as ex:
            errors[addon_name] = f"Error in {addon_name}: {ex.code}"

    return errors


def int_between(lower, upper):
    def is_between(value):
        if isinstance(value, int) and lower <= value <= upper:
            return True
        raise SchemaError(f"should be an integer between {lower} and {upper}")

    return is_between


def float_between_with_halfstep(lower, upper):
    def is_between(value):
        is_number = isinstance(value, int) or isinstance(value, float)
        is_half_step = re.match(r"^\d+(\.[05])?$", str(value))

        if is_number and is_half_step and lower <= value <= upper:
            return True
        raise SchemaError(f"should be a number between {lower} and {upper} in increments of 0.5")

    return is_between


ENV_NAME = Regex(
    r"^([a-z][a-zA-Z0-9]*|\*)$",
    error="Environment name {} is invalid: names must only contain lowercase alphanumeric characters, or be the '*' default environment",
    # For values the "error" parameter works and outputs the custom text. For keys the custom text doesn't get reported in the exception for some reason.
)

range_validator = validate_string(r"^\d+-\d+$")
seconds_validator = validate_string(r"^\d+s$")
branch_wildcard_validator = validate_string(r"^((?!\*).)*(\*)?$")

NUMBER = Or(int, float)
DELETION_POLICY = Or("Delete", "Retain")
DB_DELETION_POLICY = Or("Delete", "Retain", "Snapshot")
DELETION_PROTECTION = bool

REDIS_PLANS = Or(
    "micro",
    "micro-ha",
    "tiny",
    "tiny-ha",
    "small",
    "small-ha",
    "medium",
    "medium-ha",
    "large",
    "large-ha",
    "x-large",
    "x-large-ha",
)

REDIS_ENGINE_VERSIONS = Or("4.0.10", "5.0.6", "6.0", "6.2", "7.0", "7.1")

REDIS_DEFINITION = {
    "type": "redis",
    Optional("environments"): {
        ENV_NAME: {
            Optional("plan"): REDIS_PLANS,
            Optional("engine"): REDIS_ENGINE_VERSIONS,
            Optional("replicas"): int_between(0, 5),
            Optional("deletion_policy"): DELETION_POLICY,
            Optional("apply_immediately"): bool,
            Optional("automatic_failover_enabled"): bool,
            Optional("instance"): str,
            Optional("multi_az_enabled"): bool,
        }
    },
}

POSTGRES_PLANS = Or(
    "tiny",
    "small",
    "small-ha",
    "small-high-io",
    "medium",
    "medium-high-io",
    "large",
    "large-ha",
    "large-high-io",
    "x-large",
    "x-large-ha",
    "x-large-high-io",
)
POSTGRES_STORAGE_TYPES = Or("gp2", "gp3", "io1", "io2")

RETENTION_POLICY = Or(
    None,
    {
        "mode": Or("GOVERNANCE", "COMPLIANCE"),
        Or("days", "years", only_one=True): int,
    },
)
POSTGRES_DEFINITION = {
    "type": "postgres",
    "version": NUMBER,
    Optional("deletion_policy"): DB_DELETION_POLICY,
    Optional("environments"): {
        ENV_NAME: {
            Optional("plan"): POSTGRES_PLANS,
            Optional("volume_size"): int_between(20, 10000),
            Optional("iops"): int_between(1000, 9950),
            Optional("snapshot_id"): str,
            Optional("deletion_policy"): DB_DELETION_POLICY,
            Optional("deletion_protection"): DELETION_PROTECTION,
            Optional("multi_az"): bool,
            Optional("storage_type"): POSTGRES_STORAGE_TYPES,
        }
    },
    Optional("objects"): [
        {
            "key": str,
            Optional("body"): str,
        }
    ],
}

AURORA_DEFINITION = {
    "type": "aurora-postgres",
    "version": NUMBER,
    Optional("deletion_policy"): DB_DELETION_POLICY,
    Optional("environments"): {
        ENV_NAME: {
            Optional("min_capacity"): float_between_with_halfstep(0.5, 128),
            Optional("max_capacity"): float_between_with_halfstep(0.5, 128),
            Optional("snapshot_id"): str,
            Optional("deletion_policy"): DB_DELETION_POLICY,
            Optional("deletion_protection"): DELETION_PROTECTION,
        }
    },
    Optional("objects"): [
        {
            "key": str,
            Optional("body"): str,
        }
    ],
}

S3_BASE = {
    Optional("readonly"): bool,
    Optional("services"): Or("__all__", [str]),
    Optional("environments"): {
        ENV_NAME: {
            "bucket_name": validate_s3_bucket_name,
            Optional("deletion_policy"): DELETION_POLICY,
            Optional("retention_policy"): RETENTION_POLICY,
            Optional("versioning"): bool,
        }
    },
}

S3_POLICY_DEFINITION = dict(S3_BASE)
S3_POLICY_DEFINITION.update({"type": "s3-policy"})

S3_DEFINITION = dict(S3_BASE)
S3_DEFINITION.update(
    {
        "type": "s3",
        Optional("objects"): [
            {
                "key": str,
                Optional("body"): str,
            }
        ],
    }
)

MONITORING_DEFINITION = {
    "type": "monitoring",
    Optional("environments"): {
        ENV_NAME: {
            Optional("enable_ops_center"): bool,
        }
    },
}

OPENSEARCH_PLANS = Or(
    "tiny", "small", "small-ha", "medium", "medium-ha", "large", "large-ha", "x-large", "x-large-ha"
)
OPENSEARCH_ENGINE_VERSIONS = Or("2.11", "2.9", "2.7", "2.5", "2.3", "1.3", "1.2", "1.1", "1.0")
OPENSEARCH_MIN_VOLUME_SIZE = 10
OPENSEARCH_MAX_VOLUME_SIZE = {
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

OPENSEARCH_DEFINITION = {
    "type": "opensearch",
    Optional("environments"): {
        ENV_NAME: {
            Optional("engine"): OPENSEARCH_ENGINE_VERSIONS,
            Optional("deletion_policy"): DELETION_POLICY,
            Optional("plan"): OPENSEARCH_PLANS,
            Optional("volume_size"): int,
            Optional("ebs_throughput"): int,
            Optional("ebs_volume_type"): str,
            Optional("instance"): str,
            Optional("instances"): int,
            Optional("master"): bool,
            Optional("es_app_log_retention_in_days"): int,
            Optional("index_slow_log_retention_in_days"): int,
            Optional("audit_log_retention_in_days"): int,
            Optional("search_slow_log_retention_in_days"): int,
        }
    },
}

ALB_DEFINITION = {
    "type": "alb",
    Optional("environments"): {
        ENV_NAME: Or(
            {
                Optional("domain_prefix"): str,
                Optional("env_root"): str,
                Optional("cdn_domains_list"): dict,
                Optional("additional_address_list"): list,
            },
            None,
        )
    },
}

PROMETHEUS_POLICY_DEFINITION = {
    "type": "prometheus-policy",
    Optional("services"): Or("__all__", [str]),
    Optional("environments"): {
        ENV_NAME: {
            "role_arn": str,
        }
    },
}

ENVIRONMENTS_DEFINITION = {
    str: Or(
        None,
        {
            Optional("accounts"): {
                "deploy": {
                    "name": str,
                    "id": str,
                },
                "dns": {
                    "name": str,
                    "id": str,
                },
            },
            Optional("requires_approval"): bool,
            Optional("vpc"): str,
        },
    ),
}

CODEBASE_PIPELINES_DEFINITION = [
    {
        "name": str,
        "repository": str,
        Optional("additional_ecr_repository"): str,
        "services": list[str],
        "pipelines": [
            Or(
                {
                    "name": str,
                    "branch": branch_wildcard_validator,
                    "environments": [
                        {
                            "name": str,
                            Optional("requires_approval"): bool,
                        }
                    ],
                },
                {
                    "name": str,
                    "tag": bool,
                    "environments": [
                        {
                            "name": str,
                            Optional("requires_approval"): bool,
                        }
                    ],
                },
            ),
        ],
    },
]

ENVIRONMENT_PIPELINES_DEFINITION = {
    str: {
        Optional("branch", default="main"): str,
        "slack_channel": str,
        "trigger_on_push": bool,
        "environments": ENVIRONMENTS_DEFINITION,
    }
}

PLATFORM_CONFIG_SCHEMA = Schema(
    {
        # The following line is for the AWS Copilot version, will be removed under DBTP-1002
        "application": str,
        Optional("legacy_project", default=False): bool,
        Optional("accounts"): list[str],
        Optional("environments"): ENVIRONMENTS_DEFINITION,
        Optional("codebase_pipelines"): CODEBASE_PIPELINES_DEFINITION,
        Optional("extensions"): {
            str: Or(
                REDIS_DEFINITION,
                AURORA_DEFINITION,
                POSTGRES_DEFINITION,
                S3_DEFINITION,
                S3_POLICY_DEFINITION,
                MONITORING_DEFINITION,
                OPENSEARCH_DEFINITION,
                ALB_DEFINITION,
                PROMETHEUS_POLICY_DEFINITION,
            )
        },
        Optional("environment_pipelines"): ENVIRONMENT_PIPELINES_DEFINITION,
    }
)


S3_SCHEMA = Schema(S3_DEFINITION)
S3_POLICY_SCHEMA = Schema(S3_POLICY_DEFINITION)
AURORA_SCHEMA = Schema(AURORA_DEFINITION)
POSTGRES_SCHEMA = Schema(POSTGRES_DEFINITION)
REDIS_SCHEMA = Schema(REDIS_DEFINITION)


class ConditionalSchema(Schema):
    def validate(self, data, _is_conditional_schema=True):
        data = super(ConditionalSchema, self).validate(data, _is_conditional_schema=False)
        if _is_conditional_schema:
            default_plan = None
            default_volume_size = None

            default_environment_config = data["environments"].get(
                "*", data["environments"].get("default", None)
            )
            if default_environment_config:
                default_plan = default_environment_config.get("plan", None)
                default_volume_size = default_environment_config.get("volume_size", None)

            for env in data["environments"]:
                volume_size = data["environments"][env].get("volume_size", default_volume_size)
                plan = data["environments"][env].get("plan", default_plan)

                if volume_size:
                    if not plan:
                        raise SchemaError(f"Missing key: 'plan'")

                    if volume_size < OPENSEARCH_MIN_VOLUME_SIZE:
                        raise SchemaError(
                            f"Key 'environments' error: Key '{env}' error: Key 'volume_size' error: should be an integer greater than {OPENSEARCH_MIN_VOLUME_SIZE}"
                        )

                    for key in OPENSEARCH_MAX_VOLUME_SIZE:
                        if plan == key and not volume_size <= OPENSEARCH_MAX_VOLUME_SIZE[key]:
                            raise SchemaError(
                                f"Key 'environments' error: Key '{env}' error: Key 'volume_size' error: should be an integer between {OPENSEARCH_MIN_VOLUME_SIZE} and {OPENSEARCH_MAX_VOLUME_SIZE[key]} for plan {plan}"
                            )

        return data


OPENSEARCH_SCHEMA = ConditionalSchema(OPENSEARCH_DEFINITION)
MONITORING_SCHEMA = Schema(MONITORING_DEFINITION)
ALB_SCHEMA = Schema(ALB_DEFINITION)
PROMETHEUS_POLICY_SCHEMA = Schema(PROMETHEUS_POLICY_DEFINITION)


def no_param_schema(schema_type):
    return Schema({"type": schema_type, Optional("services"): Or("__all__", [str])})


SCHEMA_MAP = {
    "s3": S3_SCHEMA,
    "s3-policy": S3_POLICY_SCHEMA,
    "aurora-postgres": AURORA_SCHEMA,
    "postgres": POSTGRES_SCHEMA,
    "redis": REDIS_SCHEMA,
    "opensearch": OPENSEARCH_SCHEMA,
    "monitoring": MONITORING_SCHEMA,
    "appconfig-ipfilter": no_param_schema("appconfig-ipfilter"),
    "subscription-filter": no_param_schema("subscription-filter"),
    "vpc": no_param_schema("vpc"),
    "xray": no_param_schema("xray"),
    "alb": ALB_SCHEMA,
    "prometheus-policy": PROMETHEUS_POLICY_SCHEMA,
}
