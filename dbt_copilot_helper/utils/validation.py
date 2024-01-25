import re
from pathlib import Path

import yaml
from schema import Optional
from schema import Or
from schema import Regex
from schema import Schema
from schema import SchemaError


def validate_string(regex_pattern):
    def validator(string):
        if not re.match(regex_pattern, string):
            raise SchemaError(
                f"String '{string}' does not match the required pattern '{regex_pattern}'. For more details on valid string patterns see: https://aws.github.io/copilot-cli/docs/manifest/lb-web-service/"
            )
        return string

    return validator


def validate_s3_bucket_name(name):
    return False


def validate_addons(addons_file: Path | str):
    """
    Validate the addons file and return a dictionary of addon: error message.
    """
    schemas = {"s3": S3_SCHEMA, "aurora-postgres": AURORA_SCHEMA, "rds-postgres": RDS_SCHEMA}

    with open(addons_file) as fh:
        addons = yaml.safe_load(fh)

    errors = {}

    for addon_name, addon in addons.items():
        try:
            addon_type = addon.get("type", None)
            if not addon_type:
                errors[addon_name] = f"Missing addon type in addon '{addon_name}'"
                continue
            schema = schemas.get(addon_type, None)
            if not schema:
                errors[
                    addon_name
                ] = f"Unsupported addon type '{addon_type}' in addon '{addon_name}'"
                continue
            schema.validate(addon)
        except SchemaError as ex:
            errors[addon_name] = f"Error in {addon_name}: {ex.code}"

    return errors


def int_between(lower, upper):
    def is_between(value):
        if isinstance(value, int) and lower <= value <= upper:
            return True
        raise SchemaError(f"should be an int between {lower} and {upper}")

    return is_between


def float_between_with_halfstep(lower, upper):
    def is_between(value):
        is_number = isinstance(value, int) or isinstance(value, float)
        is_half_step = re.match(r"^\d+(\.[05])?$", str(value))

        if is_number and is_half_step and lower <= value <= upper:
            return True
        raise SchemaError(f"should be a number between {lower} and {upper} in half steps")

    return is_between


range_validator = validate_string(r"^\d+-\d+$")
seconds_validator = validate_string(r"^\d+s$")

BOOTSTRAP_SCHEMA = Schema(
    {
        "app": str,
        "environments": {str: {Optional("certificate_arns"): [str]}},
        "services": [
            {
                "name": str,
                "type": lambda s: s
                in (
                    "public",
                    "backend",
                ),
                "repo": str,
                "image_location": str,
                Optional("notes"): str,
                Optional("secrets_from"): str,
                "environments": {
                    str: {
                        "paas": str,
                        Optional("url"): str,
                        Optional("ipfilter"): bool,
                        Optional("memory"): int,
                        Optional("count"): Or(
                            int,
                            {
                                # https://aws.github.io/copilot-cli/docs/manifest/lb-web-service/#count
                                "range": range_validator,  # e.g. 1-10
                                Optional("cooldown"): {
                                    "in": seconds_validator,  # e.g 30s
                                    "out": seconds_validator,  # e.g 30s
                                },
                                Optional("cpu_percentage"): int,
                                Optional("memory_percentage"): Or(
                                    int,
                                    {
                                        "value": int,
                                        "cooldown": {
                                            "in": seconds_validator,  # e.g. 80s
                                            "out": seconds_validator,  # e.g 160s
                                        },
                                    },
                                ),
                                Optional("requests"): int,
                                Optional("response_time"): seconds_validator,  # e.g. 2s
                            },
                        ),
                    },
                },
                Optional("backing-services"): [
                    {
                        "name": str,
                        "type": lambda s: s
                        in (
                            "s3",
                            "s3-policy",
                            "aurora-postgres",
                            "rds-postgres",
                            "redis",
                            "opensearch",
                        ),
                        Optional("paas-description"): str,
                        Optional("paas-instance"): str,
                        Optional("notes"): str,
                        Optional("bucket_name"): str,  # for external-s3 type
                        Optional("readonly"): bool,  # for external-s3 type
                        Optional("shared"): bool,
                    },
                ],
                Optional("overlapping_secrets"): [str],
                "secrets": {
                    Optional(str): str,
                },
                "env_vars": {
                    Optional(str): str,
                },
            },
        ],
    },
)

PIPELINES_SCHEMA = Schema(
    {
        Optional("accounts"): list[str],
        Optional("environments"): [
            {
                "name": str,
                Optional("requires_approval"): bool,
            },
        ],
        Optional("codebases"): [
            {
                "name": str,
                "repository": str,
                "services": list[str],
                "pipelines": [
                    Or(
                        {
                            "name": str,
                            "branch": str,
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
        ],
    },
)

NUMBER = Or(int, float)
DELETION_POLICY = Or("Delete", "Retain", "Snapshot")
DELETION_PROTECTION = bool
RDS_PLANS = Or(
    "tiny", "small", "small-ha", "medium", "medium-ha", "large", "large-ha", "xlarge", "xlarge-ha"
)
RDS_INSTANCE_TYPES = Or(
    "db.m5.2xlarge", "db.m5.4xlarge", "db.m5.large", "db.t3.micro", "db.t3.small"
)

S3_SCHEMA = Schema(
    {
        "type": "s3",
        Optional("bucket-name"): Regex(
            r"^(?!(^xn--|.+-s3alias$))^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$"
        ),
        Optional("readonly"): bool,
        Optional("deletion-policy"): DELETION_POLICY,
        Optional("services"): [str],
        Optional("environments"): {
            str: {
                Optional("bucket-name"): Regex(
                    r"^(?!(^xn--|.+-s3alias$))^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$"
                ),
                Optional("deletion-policy"): Or("Delete", "Retain", "Snapshot"),
            }
        },
        Optional("objects"): [
            {
                "key": str,
                Optional("body"): str,
            }
        ],
    }
)

AURORA_SCHEMA = Schema(
    {
        "type": "aurora-postgres",
        "version": NUMBER,
        Optional("deletion-policy"): DELETION_POLICY,
        Optional("deletion-protection"): DELETION_PROTECTION,
        Optional("environments"): {
            str: {
                Optional("min-capacity"): float_between_with_halfstep(0.5, 128),
                Optional("max-capacity"): float_between_with_halfstep(0.5, 128),
                Optional("snapshot-id"): str,
                Optional("deletion-policy"): DELETION_POLICY,
                Optional("deletion-protection"): DELETION_PROTECTION,
            }
        },
        Optional("objects"): [
            {
                "key": str,
                Optional("body"): str,
            }
        ],
    }
)

RDS_SCHEMA = Schema(
    {
        "type": "rds-postgres",
        "version": NUMBER,
        Optional("deletion-policy"): DELETION_POLICY,
        Optional("deletion-protection"): DELETION_PROTECTION,
        Optional("environments"): {
            str: {
                Optional("plan"): RDS_PLANS,
                Optional("instance"): RDS_INSTANCE_TYPES,
                Optional("volume-size"): int_between(5, 10000),
                Optional("replicas"): int_between(0, 5),
                Optional("snapshot-id"): str,
                Optional("deletion-policy"): DELETION_POLICY,
                Optional("deletion-protection"): DELETION_PROTECTION,
            }
        },
        Optional("objects"): [
            {
                "key": str,
                Optional("body"): str,
            }
        ],
    }
)
