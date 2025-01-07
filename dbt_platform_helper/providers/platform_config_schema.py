import ipaddress
import re
from typing import Callable

from schema import Optional
from schema import Or
from schema import Regex
from schema import Schema
from schema import SchemaError


class PlatformConfigSchema:
    @staticmethod
    def schema() -> Schema:
        return Schema(
            {
                # The following line is for the AWS Copilot version, will be removed under DBTP-1002
                "application": str,
                Optional("legacy_project", default=False): bool,
                Optional("default_versions"): PlatformConfigSchema.__default_versions_schema(),
                Optional("accounts"): list[str],
                Optional("environments"): PlatformConfigSchema.__environments_schema(),
                Optional("codebase_pipelines"): PlatformConfigSchema.__codebase_pipelines_schema(),
                Optional(
                    "environment_pipelines"
                ): PlatformConfigSchema.__environment_pipelines_schema(),
                Optional("extensions"): {
                    str: Or(
                        PlatformConfigSchema.__alb_schema(),
                        PlatformConfigSchema.__monitoring_schema(),
                        PlatformConfigSchema.__opensearch_schema(),
                        PlatformConfigSchema.__postgres_schema(),
                        PlatformConfigSchema.__prometheus_policy_schema(),
                        PlatformConfigSchema.__redis_schema(),
                        PlatformConfigSchema.__s3_bucket_schema(),
                        PlatformConfigSchema.__s3_bucket_policy_schema(),
                    )
                },
            }
        )

    @staticmethod
    def extension_schemas() -> dict:
        return {
            "alb": Schema(PlatformConfigSchema.__alb_schema()),
            "appconfig-ipfilter": PlatformConfigSchema.__no_configuration_required_schema(
                "appconfig-ipfilter"
            ),
            "opensearch": ConditionalOpensSearchSchema(PlatformConfigSchema.__opensearch_schema()),
            "postgres": Schema(PlatformConfigSchema.__postgres_schema()),
            "prometheus-policy": Schema(PlatformConfigSchema.__prometheus_policy_schema()),
            "redis": Schema(PlatformConfigSchema.__redis_schema()),
            "s3": Schema(PlatformConfigSchema.__s3_bucket_schema()),
            "s3-policy": Schema(PlatformConfigSchema.__s3_bucket_policy_schema()),
            "subscription-filter": PlatformConfigSchema.__no_configuration_required_schema(
                "subscription-filter"
            ),
            # Todo: The next three are no longer relevant. Remove them.
            "monitoring": Schema(PlatformConfigSchema.__monitoring_schema()),
            "vpc": PlatformConfigSchema.__no_configuration_required_schema("vpc"),
            "xray": PlatformConfigSchema.__no_configuration_required_schema("xray"),
        }

    @staticmethod
    def __alb_schema() -> dict:
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

        return {
            "type": "alb",
            Optional("environments"): {
                PlatformConfigSchema.__valid_environment_name(): Or(
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

    @staticmethod
    def __codebase_pipelines_schema() -> list[dict]:
        return [
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
                            "branch": PlatformConfigSchema.__valid_branch_name(),
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

    @staticmethod
    def __default_versions_schema() -> dict:
        return {
            Optional("terraform-platform-modules"): str,
            Optional("platform-helper"): str,
        }

    @staticmethod
    def __environments_schema() -> dict:
        _valid_environment_specific_version_overrides = {
            Optional("terraform-platform-modules"): str,
        }

        return {
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
                    # Todo: requires_approval is no longer relevant since we don't have AWS Copilot manage environment pipelines
                    Optional("requires_approval"): bool,
                    Optional("versions"): _valid_environment_specific_version_overrides,
                    Optional("vpc"): str,
                },
            )
        }

    @staticmethod
    def __environment_pipelines_schema() -> dict:
        _valid_environment_pipeline_specific_version_overrides = {
            Optional("platform-helper"): str,
        }

        return {
            str: {
                Optional("account"): str,
                Optional("branch", default="main"): PlatformConfigSchema.__valid_branch_name(),
                Optional("pipeline_to_trigger"): str,
                Optional("versions"): _valid_environment_pipeline_specific_version_overrides,
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
                            Optional(
                                "versions"
                            ): _valid_environment_pipeline_specific_version_overrides,
                            Optional("vpc"): str,
                        },
                    )
                },
            }
        }

    @staticmethod
    def __monitoring_schema() -> dict:
        return {
            "type": "monitoring",
            Optional("environments"): {
                PlatformConfigSchema.__valid_environment_name(): {
                    Optional("enable_ops_center"): bool,
                }
            },
        }

    @staticmethod
    def __opensearch_schema() -> dict:
        # Todo: Move to OpenSearch provider?
        _valid_opensearch_plans = Or(
            "tiny",
            "small",
            "small-ha",
            "medium",
            "medium-ha",
            "large",
            "large-ha",
            "x-large",
            "x-large-ha",
        )

        return {
            "type": "opensearch",
            Optional("environments"): {
                PlatformConfigSchema.__valid_environment_name(): {
                    Optional("engine"): str,
                    Optional("deletion_policy"): PlatformConfigSchema.__valid_deletion_policy(),
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

    @staticmethod
    def __postgres_schema() -> dict:
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
            "2x-large",
            "2x-large-ha",
            "2x-large-high-io",
            "4x-large",
            "4x-large-ha",
            "4x-large-high-io",
        )

        # Todo: Move to Postgres provider?
        _valid_postgres_storage_types = Or("gp2", "gp3", "io1", "io2")

        _valid_postgres_database_copy = {
            "from": PlatformConfigSchema.__valid_environment_name(),
            "to": PlatformConfigSchema.__valid_environment_name(),
            Optional("from_account"): str,
            Optional("to_account"): str,
            Optional("pipeline"): {Optional("schedule"): str},
        }

        return {
            "type": "postgres",
            "version": (Or(int, float)),
            Optional("deletion_policy"): PlatformConfigSchema.__valid_postgres_deletion_policy(),
            Optional("environments"): {
                PlatformConfigSchema.__valid_environment_name(): {
                    Optional("plan"): _valid_postgres_plans,
                    Optional("volume_size"): PlatformConfigSchema.is_integer_between(20, 10000),
                    Optional("iops"): PlatformConfigSchema.is_integer_between(1000, 9950),
                    Optional("snapshot_id"): str,
                    Optional(
                        "deletion_policy"
                    ): PlatformConfigSchema.__valid_postgres_deletion_policy(),
                    Optional("deletion_protection"): bool,
                    Optional("multi_az"): bool,
                    Optional("storage_type"): _valid_postgres_storage_types,
                    Optional("backup_retention_days"): PlatformConfigSchema.is_integer_between(
                        1, 35
                    ),
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

    @staticmethod
    def __prometheus_policy_schema() -> dict:
        return {
            "type": "prometheus-policy",
            Optional("services"): Or("__all__", [str]),
            Optional("environments"): {
                PlatformConfigSchema.__valid_environment_name(): {
                    "role_arn": str,
                }
            },
        }

    @staticmethod
    def __redis_schema() -> dict:
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

        return {
            "type": "redis",
            Optional("environments"): {
                PlatformConfigSchema.__valid_environment_name(): {
                    Optional("plan"): _valid_redis_plans,
                    Optional("engine"): str,
                    Optional("replicas"): PlatformConfigSchema.is_integer_between(0, 5),
                    Optional("deletion_policy"): PlatformConfigSchema.__valid_deletion_policy(),
                    Optional("apply_immediately"): bool,
                    Optional("automatic_failover_enabled"): bool,
                    Optional("instance"): str,
                    Optional("multi_az_enabled"): bool,
                }
            },
        }

    @staticmethod
    def valid_s3_bucket_name(name: str):
        # Todo: This is a public method becasue that's what the test expect. Perhaps it belongs in an S3 provider?
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

    @staticmethod
    def __valid_s3_base_definition() -> dict:
        def _valid_s3_bucket_arn(key):
            return Regex(
                r"^arn:aws:s3::.*",
                error=f"{key} must contain a valid ARN for an S3 bucket",
            )

        _valid_s3_data_migration = {
            "import": {
                Optional("source_kms_key_arn"): PlatformConfigSchema.__valid_kms_key_arn(
                    "source_kms_key_arn"
                ),
                "source_bucket_arn": _valid_s3_bucket_arn("source_bucket_arn"),
                "worker_role_arn": PlatformConfigSchema.__valid_iam_role_arn("worker_role_arn"),
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
            "role_arn": PlatformConfigSchema.__valid_iam_role_arn("role_arn"),
            "read": bool,
            "write": bool,
            "cyber_sign_off_by": PlatformConfigSchema.__valid_dbt_email_address(
                "cyber_sign_off_by"
            ),
        }

        _valid_s3_bucket_external_role_access_name = Regex(
            r"^([a-z][a-zA-Z0-9_-]*)$",
            error="External role access block name {} is invalid: names must only contain lowercase alphanumeric characters separated by hypen or underscore",
        )

        return dict(
            {
                Optional("readonly"): bool,
                Optional("serve_static_content"): bool,
                Optional("serve_static_param_name"): str,
                Optional("services"): Or("__all__", [str]),
                Optional("environments"): {
                    PlatformConfigSchema.__valid_environment_name(): {
                        "bucket_name": PlatformConfigSchema.valid_s3_bucket_name,
                        Optional("deletion_policy"): PlatformConfigSchema.__valid_deletion_policy(),
                        Optional("retention_policy"): _valid_s3_bucket_retention_policy,
                        Optional("versioning"): bool,
                        Optional("lifecycle_rules"): [_valid_s3_bucket_lifecycle_rule],
                        Optional("data_migration"): _valid_s3_data_migration,
                        Optional("external_role_access"): {
                            PlatformConfigSchema.__valid_schema_key(): _valid_s3_bucket_external_role_access
                        },
                        Optional("cross_environment_service_access"): {
                            PlatformConfigSchema.__valid_schema_key(): {
                                "application": str,
                                "environment": PlatformConfigSchema.__valid_environment_name(),
                                "account": str,
                                "service": str,
                                "read": bool,
                                "write": bool,
                                "cyber_sign_off_by": PlatformConfigSchema.__valid_dbt_email_address(
                                    "cyber_sign_off_by"
                                ),
                            }
                        },
                    },
                },
            }
        )

    @staticmethod
    def __s3_bucket_schema() -> dict:
        return PlatformConfigSchema.__valid_s3_base_definition() | {
            "type": "s3",
            Optional("objects"): [
                {"key": str, Optional("body"): str, Optional("content_type"): str}
            ],
        }

    @staticmethod
    def __s3_bucket_policy_schema() -> dict:
        return PlatformConfigSchema.__valid_s3_base_definition() | {"type": "s3-policy"}

    @staticmethod
    def string_matching_regex(regex_pattern: str) -> Callable:
        # Todo public for the unit tests, not sure about testing what could be a private method. Perhaps it's covered by other tests anyway?
        def validate(string):
            if not re.match(regex_pattern, string):
                # Todo: Raise suitable PlatformException?
                raise SchemaError(
                    f"String '{string}' does not match the required pattern '{regex_pattern}'."
                )
            return string

        return validate

    @staticmethod
    def is_integer_between(lower_limit, upper_limit) -> Callable:
        # Todo public for the unit tests, not sure about testing what could be a private method. Perhaps it's covered by other tests anyway?
        def validate(value):
            if isinstance(value, int) and lower_limit <= value <= upper_limit:
                return True
            # Todo: Raise suitable PlatformException?
            raise SchemaError(f"should be an integer between {lower_limit} and {upper_limit}")

        return validate

    @staticmethod
    def __valid_schema_key() -> Regex:
        return Regex(
            r"^([a-z][a-zA-Z0-9_-]*|\*)$",
            error="{} is invalid: must only contain lowercase alphanumeric characters separated by hyphen or underscore",
        )

    @staticmethod
    def __valid_branch_name() -> Callable:
        # Todo: Make this actually validate a git branch name properly; https://git-scm.com/docs/git-check-ref-format
        return PlatformConfigSchema.string_matching_regex(r"^((?!\*).)*(\*)?$")

    @staticmethod
    def __valid_deletion_policy() -> Or:
        return Or("Delete", "Retain")

    @staticmethod
    def __valid_postgres_deletion_policy() -> Or:
        return Or("Delete", "Retain", "Snapshot")

    @staticmethod
    def __valid_environment_name() -> Regex:
        return Regex(
            r"^([a-z][a-zA-Z0-9]*|\*)$",
            error="Environment name {} is invalid: names must only contain lowercase alphanumeric characters, or be the '*' default environment",
            # For values the "error" parameter works and outputs the custom text. For keys the custom text doesn't get reported in the exception for some reason.
        )

    @staticmethod
    def __valid_kms_key_arn(key) -> Regex:
        return Regex(
            r"^arn:aws:kms:.*:\d{12}:(key|alias).*",
            error=f"{key} must contain a valid ARN for a KMS key",
        )

    @staticmethod
    def __valid_iam_role_arn(key) -> Regex:
        return Regex(
            r"^arn:aws:iam::\d{12}:role/.*",
            error=f"{key} must contain a valid ARN for an IAM role",
        )

    @staticmethod
    def __valid_dbt_email_address(key) -> Regex:
        return Regex(
            r"^[\w.-]+@(businessandtrade.gov.uk|digital.trade.gov.uk)$",
            error=f"{key} must contain a valid DBT email address",
        )

    @staticmethod
    def __no_configuration_required_schema(schema_type) -> Schema:
        return Schema({"type": schema_type, Optional("services"): Or("__all__", [str])})


class ConditionalOpensSearchSchema(Schema):
    # Todo: Move to OpenSearch provider?
    _valid_opensearch_min_volume_size: int = 10

    # Todo: Move to OpenSearch provider?
    _valid_opensearch_max_volume_size: dict = {
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

    def validate(self, data, _is_conditional_schema=True) -> Schema:
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

                    if volume_size < self._valid_opensearch_min_volume_size:
                        # Todo: Raise suitable PlatformException?
                        raise SchemaError(
                            f"Key 'environments' error: Key '{env}' error: Key 'volume_size' error: should be an integer greater than {self._valid_opensearch_min_volume_size}"
                        )

                    for key in self._valid_opensearch_max_volume_size:
                        if (
                            plan == key
                            and not volume_size <= self._valid_opensearch_max_volume_size[key]
                        ):
                            # Todo: Raise suitable PlatformException?
                            raise SchemaError(
                                f"Key 'environments' error: Key '{env}' error: Key 'volume_size' error: should be an integer between {self._valid_opensearch_min_volume_size} and {self._valid_opensearch_max_volume_size[key]} for plan {plan}"
                            )

        return data
