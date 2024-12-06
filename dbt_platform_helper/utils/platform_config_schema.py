import ipaddress
import re

from schema import Optional
from schema import Or
from schema import Regex
from schema import Schema
from schema import SchemaError

# Todo move to Redis provider?
_valid_redis_plans = Or(
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

# Todo: Move to Postgres provider?
_valid_postgres_plans = Or(
    "tiny",
    "small",
    "small-ha",
    "small-high-io",
    "medium",
    "medium-ha",
    "medium-high-io",
    "large",
    "large-ha",
    "large-high-io",
    "x-large",
    "x-large-ha",
    "x-large-high-io",
)
_valid_postgres_storage_types = Or("gp2", "gp3", "io1", "io2")


def _create_string_regex_validator(regex_pattern: str):
    def validator(string):
        if not re.match(regex_pattern, string):
            raise SchemaError(
                f"String '{string}' does not match the required pattern '{regex_pattern}'. For more details on valid string patterns see: https://aws.github.io/copilot-cli/docs/manifest/lb-web-service/"
            )
        return string

    return validator


def _create_int_between_validator(lower, upper):
    def _is_between(value):
        if isinstance(value, int) and lower <= value <= upper:
            return True
        raise SchemaError(f"should be an integer between {lower} and {upper}")

    return _is_between


_branch_wildcard_validator = _create_string_regex_validator(r"^((?!\*).)*(\*)?$")
_valid_deletion_policy = Or("Delete", "Retain")
_valid_postgres_deletion_policy = Or("Delete", "Retain", "Snapshot")

_valid_environment_name = Regex(
    r"^([a-z][a-zA-Z0-9]*|\*)$",
    error="Environment name {} is invalid: names must only contain lowercase alphanumeric characters, or be the '*' default environment",
    # For values the "error" parameter works and outputs the custom text. For keys the custom text doesn't get reported in the exception for some reason.
)

_valid_retention_policy = Or(
    None,
    {
        "mode": Or("GOVERNANCE", "COMPLIANCE"),
        Or("days", "years", only_one=True): int,
    },
)

_valid_redis = {
    "type": "redis",
    Optional("environments"): {
        _valid_environment_name: {
            Optional("plan"): _valid_redis_plans,
            Optional("engine"): str,
            Optional("replicas"): _create_int_between_validator(0, 5),
            Optional("deletion_policy"): _valid_deletion_policy,
            Optional("apply_immediately"): bool,
            Optional("automatic_failover_enabled"): bool,
            Optional("instance"): str,
            Optional("multi_az_enabled"): bool,
        }
    },
}

_valida_database_copy_specification = {
    "from": _valid_environment_name,
    "to": _valid_environment_name,
    Optional("from_account"): str,
    Optional("to_account"): str,
}

_valid_postgres = {
    "type": "postgres",
    "version": (Or(int, float)),
    Optional("deletion_policy"): _valid_postgres_deletion_policy,
    Optional("environments"): {
        _valid_environment_name: {
            Optional("plan"): _valid_postgres_plans,
            Optional("volume_size"): _create_int_between_validator(20, 10000),
            Optional("iops"): _create_int_between_validator(1000, 9950),
            Optional("snapshot_id"): str,
            Optional("deletion_policy"): _valid_postgres_deletion_policy,
            Optional("deletion_protection"): bool,
            Optional("multi_az"): bool,
            Optional("storage_type"): _valid_postgres_storage_types,
            Optional("backup_retention_days"): _create_int_between_validator(1, 35),
        }
    },
    Optional("database_copy"): [_valida_database_copy_specification],
    Optional("objects"): [
        {
            "key": str,
            Optional("body"): str,
        }
    ],
}

_valid_s3_bucket_lifecycle_rule = {
    Optional("filter_prefix"): str,
    "expiration_days": int,
    "enabled": bool,
}


def kms_key_arn_regex(key):
    return Regex(
        r"^arn:aws:kms:.*:\d{12}:(key|alias).*",
        error=f"{key} must contain a valid ARN for a KMS key",
    )


def s3_bucket_arn_regex(key):
    return Regex(
        r"^arn:aws:s3::.*",
        error=f"{key} must contain a valid ARN for an S3 bucket",
    )


def iam_role_arn_regex(key):
    return Regex(
        r"^arn:aws:iam::\d{12}:role/.*",
        error=f"{key} must contain a valid ARN for an IAM role",
    )


def dbt_email_address_regex(key):
    return Regex(
        r"^[\w.-]+@(businessandtrade.gov.uk|digital.trade.gov.uk)$",
        error=f"{key} must contain a valid DBT email address",
    )


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

    if errors:
        # Todo: Raise suitable PlatformException
        raise SchemaError(
            "Bucket name '{}' is invalid:\n{}".format(name, "\n".join(f"  {e}" for e in errors))
        )

    return True


EXTERNAL_ROLE_ACCESS = {
    "role_arn": iam_role_arn_regex("role_arn"),
    "read": bool,
    "write": bool,
    "cyber_sign_off_by": dbt_email_address_regex("cyber_sign_off_by"),
}

EXTERNAL_ROLE_ACCESS_NAME = Regex(
    r"^([a-z][a-zA-Z0-9_-]*)$",
    error="External role access block name {} is invalid: names must only contain lowercase alphanumeric characters separated by hypen or underscore",
)

DATA_IMPORT = {
    Optional("source_kms_key_arn"): kms_key_arn_regex("source_kms_key_arn"),
    "source_bucket_arn": s3_bucket_arn_regex("source_bucket_arn"),
    "worker_role_arn": iam_role_arn_regex("worker_role_arn"),
}

DATA_MIGRATION = {
    "import": DATA_IMPORT,
}

_valid_s3_base_definition = dict(
    {
        Optional("readonly"): bool,
        Optional("serve_static_content"): bool,
        Optional("services"): Or("__all__", [str]),
        Optional("environments"): {
            _valid_environment_name: {
                "bucket_name": validate_s3_bucket_name,
                Optional("deletion_policy"): _valid_deletion_policy,
                Optional("retention_policy"): _valid_retention_policy,
                Optional("versioning"): bool,
                Optional("lifecycle_rules"): [_valid_s3_bucket_lifecycle_rule],
                Optional("data_migration"): DATA_MIGRATION,
                Optional("external_role_access"): {EXTERNAL_ROLE_ACCESS_NAME: EXTERNAL_ROLE_ACCESS},
            },
        },
    }
)

_valid_s3_bucket = _valid_s3_base_definition | {
    "type": "s3",
    Optional("objects"): [{"key": str, Optional("body"): str, Optional("content_type"): str}],
}

_valid_s3_bucket_policy = _valid_s3_base_definition | {"type": "s3-policy"}

_valid_monitoring = {
    "type": "monitoring",
    Optional("environments"): {
        _valid_environment_name: {
            Optional("enable_ops_center"): bool,
        }
    },
}

OPENSEARCH_PLANS = Or(
    "tiny", "small", "small-ha", "medium", "medium-ha", "large", "large-ha", "x-large", "x-large-ha"
)
OPENSEARCH_ENGINE_VERSIONS = str
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

_valid_opensearch = {
    "type": "opensearch",
    Optional("environments"): {
        _valid_environment_name: {
            Optional("engine"): OPENSEARCH_ENGINE_VERSIONS,
            Optional("deletion_policy"): _valid_deletion_policy,
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
            Optional("password_special_characters"): str,
            Optional("urlencode_password"): bool,
        }
    },
}

CACHE_POLICY_DEFINITION = {
    "min_ttl": int,
    "max_ttl": int,
    "default_ttl": int,
    "cookies_config": Or("none", "whitelist", "allExcept", "all"),
    "header": Or("none", "whitelist"),
    "query_string_behavior": Or("none", "whitelist", "allExcept", "all"),
    Optional("cookie_list"): list,
    Optional("headers_list"): list,
    Optional("cache_policy_query_strings"): list,
}

PATHS_DEFINITION = {
    Optional("default"): {
        "cache": str,
        "request": str,
    },
    Optional("additional"): list[
        {
            "path": str,
            "cache": str,
            "request": str,
        }
    ],
}

_valid_alb = {
    "type": "alb",
    Optional("environments"): {
        _valid_environment_name: Or(
            {
                Optional("additional_address_list"): list,
                Optional("allowed_methods"): list,
                Optional("cached_methods"): list,
                Optional("cdn_compress"): bool,
                Optional("cdn_domains_list"): dict,
                Optional("cdn_geo_locations"): list,
                Optional("cdn_geo_restriction_type"): str,
                Optional("cdn_logging_bucket"): str,
                Optional("cdn_logging_bucket_prefix"): str,
                Optional("cdn_timeout_seconds"): int,
                Optional("default_waf"): str,
                Optional("domain_prefix"): str,
                Optional("enable_logging"): bool,
                Optional("env_root"): str,
                Optional("forwarded_values_forward"): str,
                Optional("forwarded_values_headers"): list,
                Optional("forwarded_values_query_string"): bool,
                Optional("origin_protocol_policy"): str,
                Optional("origin_ssl_protocols"): list,
                Optional("slack_alert_channel_alb_secret_rotation"): str,
                Optional("viewer_certificate_minimum_protocol_version"): str,
                Optional("viewer_certificate_ssl_support_method"): str,
                Optional("viewer_protocol_policy"): str,
                Optional("cache_policy"): dict({str: CACHE_POLICY_DEFINITION}),
                Optional("origin_request_policy"): dict({str: {}}),
                Optional("paths"): dict({str: PATHS_DEFINITION}),
            },
            None,
        )
    },
}

_valid_prometheus_policy = {
    "type": "prometheus-policy",
    Optional("services"): Or("__all__", [str]),
    Optional("environments"): {
        _valid_environment_name: {
            "role_arn": str,
        }
    },
}

_DEFAULT_VERSIONS_DEFINITION = {
    Optional("terraform-platform-modules"): str,
    Optional("platform-helper"): str,
}
_ENVIRONMENTS_VERSIONS_OVERRIDES = {
    Optional("terraform-platform-modules"): str,
}
_PIPELINE_VERSIONS_OVERRIDES = {
    Optional("platform-helper"): str,
}

_ENVIRONMENTS_PARAMS = {
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
    Optional("versions"): _ENVIRONMENTS_VERSIONS_OVERRIDES,
    Optional("vpc"): str,
}

ENVIRONMENTS_DEFINITION = {str: Or(None, _ENVIRONMENTS_PARAMS)}

CODEBASE_PIPELINES_DEFINITION = [
    {
        "name": str,
        "repository": str,
        Optional("additional_ecr_repository"): str,
        Optional("deploy_repository_branch"): str,
        "services": list[str],
        "pipelines": [
            Or(
                {
                    "name": str,
                    "branch": _branch_wildcard_validator,
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
        Optional("account"): str,
        Optional("branch", default="main"): str,
        Optional("pipeline_to_trigger"): str,
        Optional("versions"): _PIPELINE_VERSIONS_OVERRIDES,
        "slack_channel": str,
        "trigger_on_push": bool,
        "environments": {str: Or(None, _ENVIRONMENTS_PARAMS)},
    }
}


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


def _no_configuration_required_schema(schema_type):
    return Schema({"type": schema_type, Optional("services"): Or("__all__", [str])})


# Used outside this file by validate_platform_config()
PLATFORM_CONFIG_SCHEMA = Schema(
    {
        # The following line is for the AWS Copilot version, will be removed under DBTP-1002
        "application": str,
        Optional("legacy_project", default=False): bool,
        Optional("default_versions"): _DEFAULT_VERSIONS_DEFINITION,
        Optional("accounts"): list[str],
        Optional("environments"): ENVIRONMENTS_DEFINITION,
        Optional("codebase_pipelines"): CODEBASE_PIPELINES_DEFINITION,
        Optional("extensions"): {
            str: Or(
                _valid_alb,
                _valid_monitoring,
                _valid_opensearch,
                _valid_postgres,
                _valid_prometheus_policy,
                _valid_redis,
                _valid_s3_bucket,
                _valid_s3_bucket_policy,
            )
        },
        Optional("environment_pipelines"): ENVIRONMENT_PIPELINES_DEFINITION,
    }
)

# This is used outside this file by validate_addons()
EXTENSION_SCHEMAS = {
    "alb": Schema(_valid_alb),
    "monitoring": Schema(_valid_monitoring),
    "opensearch": ConditionalSchema(_valid_opensearch),
    "postgres": Schema(_valid_postgres),
    "prometheus-policy": Schema(_valid_prometheus_policy),
    "redis": Schema(_valid_redis),
    "s3": Schema(_valid_s3_bucket),
    "s3-policy": Schema(_valid_s3_bucket_policy),
    "subscription-filter": _no_configuration_required_schema("subscription-filter"),
    # Todo: I think the next three are no longer relevant?
    "appconfig-ipfilter": _no_configuration_required_schema("appconfig-ipfilter"),
    "vpc": _no_configuration_required_schema("vpc"),
    "xray": _no_configuration_required_schema("xray"),
}
