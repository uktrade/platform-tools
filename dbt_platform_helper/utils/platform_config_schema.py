import ipaddress
import re

from schema import Optional
from schema import Or
from schema import Regex
from schema import Schema
from schema import SchemaError


def _string_matching_regex(regex_pattern: str):
    def validator(string):
        if not re.match(regex_pattern, string):
            # Todo: Raise suitable PlatformException?
            raise SchemaError(
                f"String '{string}' does not match the required pattern '{regex_pattern}'. For more details on valid string patterns see: https://aws.github.io/copilot-cli/docs/manifest/lb-web-service/"
            )
        return string

    return validator


def _integer_between(lower, upper):
    def _is_between(value):
        if isinstance(value, int) and lower <= value <= upper:
            return True
        # Todo: Raise suitable PlatformException?
        raise SchemaError(f"should be an integer between {lower} and {upper}")

    return _is_between


_valid_schema_key = Regex(
    r"^([a-z][a-zA-Z0-9_-]*|\*)$",
    error="{} is invalid: must only contain lowercase alphanumeric characters separated by hyphen or underscore",
)

_valid_branch_name = _string_matching_regex(r"^((?!\*).)*(\*)?$")

_valid_deletion_policy = Or("Delete", "Retain")

_valid_postgres_deletion_policy = Or("Delete", "Retain", "Snapshot")

_valid_environment_name = Regex(
    r"^([a-z][a-zA-Z0-9]*|\*)$",
    error="Environment name {} is invalid: names must only contain lowercase alphanumeric characters, or be the '*' default environment",
    # For values the "error" parameter works and outputs the custom text. For keys the custom text doesn't get reported in the exception for some reason.
)


def _valid_kms_key_arn(key):
    return Regex(
        r"^arn:aws:kms:.*:\d{12}:(key|alias).*",
        error=f"{key} must contain a valid ARN for a KMS key",
    )


def _valid_iam_role_arn(key):
    return Regex(
        r"^arn:aws:iam::\d{12}:role/.*",
        error=f"{key} must contain a valid ARN for an IAM role",
    )


def _valid_dbt_email_address(key):
    return Regex(
        r"^[\w.-]+@(businessandtrade.gov.uk|digital.trade.gov.uk)$",
        error=f"{key} must contain a valid DBT email address",
    )


_cross_environment_service_access_schema = {
    "application": str,
    "environment": _valid_environment_name,
    "account": str,
    "service": str,
    "read": bool,
    "write": bool,
    "cyber_sign_off_by": _valid_dbt_email_address("cyber_sign_off_by"),
}


def _no_configuration_required_schema(schema_type):
    return Schema({"type": schema_type, Optional("services"): Or("__all__", [str])})


# Application load balancer....
_valid_alb_cache_policy = {
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

_valid_alb_paths_definition = {
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

_alb_schema = {
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
                Optional("cache_policy"): dict({str: _valid_alb_cache_policy}),
                Optional("origin_request_policy"): dict({str: {}}),
                Optional("paths"): dict({str: _valid_alb_paths_definition}),
            },
            None,
        )
    },
}

# Monitoring...
_monitoring_schema = {
    "type": "monitoring",
    Optional("environments"): {
        _valid_environment_name: {
            Optional("enable_ops_center"): bool,
        }
    },
}


# Opensearch...
class ConditionalOpensSearchSchema(Schema):
    def validate(self, data, _is_conditional_schema=True):
        data = super(ConditionalOpensSearchSchema, self).validate(
            data, _is_conditional_schema=False
        )
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
                        # Todo: Raise suitable PlatformException?
                        raise SchemaError(f"Missing key: 'plan'")

                    if volume_size < _valid_opensearch_min_volume_size:
                        # Todo: Raise suitable PlatformException?
                        raise SchemaError(
                            f"Key 'environments' error: Key '{env}' error: Key 'volume_size' error: should be an integer greater than {_valid_opensearch_min_volume_size}"
                        )

                    for key in _valid_opensearch_max_volume_size:
                        if (
                            plan == key
                            and not volume_size <= _valid_opensearch_max_volume_size[key]
                        ):
                            # Todo: Raise suitable PlatformException?
                            raise SchemaError(
                                f"Key 'environments' error: Key '{env}' error: Key 'volume_size' error: should be an integer between {_valid_opensearch_min_volume_size} and {_valid_opensearch_max_volume_size[key]} for plan {plan}"
                            )

        return data


# Todo: Move to OpenSearch provider?
_valid_opensearch_plans = Or(
    "tiny", "small", "small-ha", "medium", "medium-ha", "large", "large-ha", "x-large", "x-large-ha"
)
# Todo: Move to OpenSearch provider?
_valid_opensearch_min_volume_size = 10
# Todo: Move to OpenSearch provider?
_valid_opensearch_max_volume_size = {
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

_opensearch_schema = {
    "type": "opensearch",
    Optional("environments"): {
        _valid_environment_name: {
            Optional("engine"): str,
            Optional("deletion_policy"): _valid_deletion_policy,
            Optional("plan"): _valid_opensearch_plans,
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

# Prometheus...
_prometheus_policy_schema = {
    "type": "prometheus-policy",
    Optional("services"): Or("__all__", [str]),
    Optional("environments"): {
        _valid_environment_name: {
            "role_arn": str,
        }
    },
}

# Postgres...
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

# Todo: Move to Postgres provider?
_valid_postgres_storage_types = Or("gp2", "gp3", "io1", "io2")

_valid_postgres_database_copy = {
    "from": _valid_environment_name,
    "to": _valid_environment_name,
    Optional("from_account"): str,
    Optional("to_account"): str,
    Optional("pipeline"): {Optional("schedule"): str},
}

_postgres_schema = {
    "type": "postgres",
    "version": (Or(int, float)),
    Optional("deletion_policy"): _valid_postgres_deletion_policy,
    Optional("environments"): {
        _valid_environment_name: {
            Optional("plan"): _valid_postgres_plans,
            Optional("volume_size"): _integer_between(20, 10000),
            Optional("iops"): _integer_between(1000, 9950),
            Optional("snapshot_id"): str,
            Optional("deletion_policy"): _valid_postgres_deletion_policy,
            Optional("deletion_protection"): bool,
            Optional("multi_az"): bool,
            Optional("storage_type"): _valid_postgres_storage_types,
            Optional("backup_retention_days"): _integer_between(1, 35),
        }
    },
    Optional("database_copy"): [_valid_postgres_database_copy],
    Optional("objects"): [
        {
            "key": str,
            Optional("body"): str,
        }
    ],
}

# Redis...
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

_redis_schema = {
    "type": "redis",
    Optional("environments"): {
        _valid_environment_name: {
            Optional("plan"): _valid_redis_plans,
            Optional("engine"): str,
            Optional("replicas"): _integer_between(0, 5),
            Optional("deletion_policy"): _valid_deletion_policy,
            Optional("apply_immediately"): bool,
            Optional("automatic_failover_enabled"): bool,
            Optional("instance"): str,
            Optional("multi_az_enabled"): bool,
        }
    },
}


# S3 Bucket...
def _valid_s3_bucket_name(name: str):
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
        # Todo: Raise suitable PlatformException?
        raise SchemaError(
            "Bucket name '{}' is invalid:\n{}".format(name, "\n".join(f"  {e}" for e in errors))
        )

    return True


def _valid_s3_bucket_arn(key):
    return Regex(
        r"^arn:aws:s3::.*",
        error=f"{key} must contain a valid ARN for an S3 bucket",
    )


_valid_s3_data_migration = {
    "import": {
        Optional("source_kms_key_arn"): _valid_kms_key_arn("source_kms_key_arn"),
        "source_bucket_arn": _valid_s3_bucket_arn("source_bucket_arn"),
        "worker_role_arn": _valid_iam_role_arn("worker_role_arn"),
    },
}

_valid_s3_bucket_retention_policy = Or(
    None,
    {
        "mode": Or("GOVERNANCE", "COMPLIANCE"),
        Or("days", "years", only_one=True): int,
    },
)

_valid_s3_bucket_lifecycle_rule = {
    Optional("filter_prefix"): str,
    "expiration_days": int,
    "enabled": bool,
}

_valid_s3_bucket_external_role_access = {
    "role_arn": _valid_iam_role_arn("role_arn"),
    "read": bool,
    "write": bool,
    "cyber_sign_off_by": _valid_dbt_email_address("cyber_sign_off_by"),
}

_valid_s3_bucket_external_role_access_name = Regex(
    r"^([a-z][a-zA-Z0-9_-]*)$",
    error="External role access block name {} is invalid: names must only contain lowercase alphanumeric characters separated by hypen or underscore",
)

_valid_s3_base_definition = dict(
    {
        Optional("readonly"): bool,
        Optional("serve_static_content"): bool,
        Optional("services"): Or("__all__", [str]),
        Optional("environments"): {
            _valid_environment_name: {
                "bucket_name": _valid_s3_bucket_name,
                Optional("deletion_policy"): _valid_deletion_policy,
                Optional("retention_policy"): _valid_s3_bucket_retention_policy,
                Optional("versioning"): bool,
                Optional("lifecycle_rules"): [_valid_s3_bucket_lifecycle_rule],
                Optional("data_migration"): _valid_s3_data_migration,
                Optional("external_role_access"): {
                    _valid_schema_key: _valid_s3_bucket_external_role_access
                },
                Optional("cross_environment_service_access"): {
                    _valid_schema_key: _cross_environment_service_access_schema
                },
            },
        },
    }
)

_s3_bucket_schema = _valid_s3_base_definition | {
    "type": "s3",
    Optional("objects"): [{"key": str, Optional("body"): str, Optional("content_type"): str}],
}

_s3_bucket_policy_schema = _valid_s3_base_definition | {"type": "s3-policy"}

_default_versions_schema = {
    Optional("terraform-platform-modules"): str,
    Optional("platform-helper"): str,
}

_valid_environment_specific_version_overrides = {
    Optional("terraform-platform-modules"): str,
}

_valid_pipeline_specific_version_overrides = {
    Optional("platform-helper"): str,
}

_environments_schema = {
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
            # Todo: Is requires_approval relevant?
            Optional("requires_approval"): bool,
            Optional("versions"): _valid_environment_specific_version_overrides,
            Optional("vpc"): str,
        },
    )
}

# Codebase pipelines...
_codebase_pipelines_schema = [
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
                    "branch": _valid_branch_name,
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

# Environment pipelines...
_environment_pipelines_schema = {
    str: {
        Optional("account"): str,
        Optional("branch", default="main"): str,
        Optional("pipeline_to_trigger"): str,
        Optional("versions"): _valid_pipeline_specific_version_overrides,
        "slack_channel": str,
        "trigger_on_push": bool,
        "environments": {
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
                    Optional("versions"): _valid_environment_specific_version_overrides,
                    Optional("vpc"): str,
                },
            )
        },
    }
}


# Used outside this file by validate_platform_config()
PLATFORM_CONFIG_SCHEMA = Schema(
    {
        # The following line is for the AWS Copilot version, will be removed under DBTP-1002
        "application": str,
        Optional("legacy_project", default=False): bool,
        Optional("default_versions"): _default_versions_schema,
        Optional("accounts"): list[str],
        Optional("environments"): _environments_schema,
        Optional("codebase_pipelines"): _codebase_pipelines_schema,
        Optional("environment_pipelines"): _environment_pipelines_schema,
        Optional("extensions"): {
            str: Or(
                _alb_schema,
                _monitoring_schema,
                _opensearch_schema,
                _postgres_schema,
                _prometheus_policy_schema,
                _redis_schema,
                _s3_bucket_schema,
                _s3_bucket_policy_schema,
            )
        },
    }
)

# This is used outside this file by validate_addons()
EXTENSION_SCHEMAS = {
    "alb": Schema(_alb_schema),
    "appconfig-ipfilter": _no_configuration_required_schema("appconfig-ipfilter"),
    "opensearch": ConditionalOpensSearchSchema(_opensearch_schema),
    "postgres": Schema(_postgres_schema),
    "prometheus-policy": Schema(_prometheus_policy_schema),
    "redis": Schema(_redis_schema),
    "s3": Schema(_s3_bucket_schema),
    "s3-policy": Schema(_s3_bucket_policy_schema),
    "subscription-filter": _no_configuration_required_schema("subscription-filter"),
    # Todo: We think the next three are no longer relevant?
    "monitoring": Schema(_monitoring_schema),
    "vpc": _no_configuration_required_schema("vpc"),
    "xray": _no_configuration_required_schema("xray"),
}
