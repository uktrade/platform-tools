import ipaddress
import os
import re
from pathlib import Path

import click
import yaml
from schema import Optional
from schema import Or
from schema import Regex
from schema import Schema
from schema import SchemaError
from yaml.parser import ParserError
from yamllint import config
from yamllint import linter

from dbt_platform_helper.constants import CODEBASE_PIPELINES_KEY
from dbt_platform_helper.constants import ENVIRONMENTS_KEY
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_FILE
from dbt_platform_helper.utils.aws import get_supported_opensearch_versions
from dbt_platform_helper.utils.aws import get_supported_redis_versions
from dbt_platform_helper.utils.files import apply_environment_defaults
from dbt_platform_helper.utils.messages import abort_with_error


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

    _validate_extension_supported_versions(
        config={"extensions": addons},
        extension_type="redis",
        version_key="engine",
        get_supported_versions_fn=get_supported_redis_versions,
    )
    _validate_extension_supported_versions(
        config={"extensions": addons},
        extension_type="opensearch",
        version_key="engine",
        get_supported_versions_fn=get_supported_opensearch_versions,
    )

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

REDIS_ENGINE_VERSIONS = str

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
    "medium-ha",
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

DATABASE_COPY = {"from": ENV_NAME, "to": ENV_NAME}

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
            Optional("backup_retention_days"): int_between(1, 35),
        }
    },
    Optional("database_copy"): [DATABASE_COPY],
    Optional("objects"): [
        {
            "key": str,
            Optional("body"): str,
        }
    ],
}

LIFECYCLE_RULE = {
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


DATA_IMPORT = {
    Optional("source_kms_key_arn"): kms_key_arn_regex("source_kms_key_arn"),
    "source_bucket_arn": s3_bucket_arn_regex("source_bucket_arn"),
    "worker_role_arn": iam_role_arn_regex("worker_role_arn"),
}

DATA_MIGRATION = {
    "import": DATA_IMPORT,
}

S3_BASE = {
    Optional("readonly"): bool,
    Optional("serve_static_content"): bool,
    Optional("services"): Or("__all__", [str]),
    Optional("environments"): {
        ENV_NAME: {
            "bucket_name": validate_s3_bucket_name,
            Optional("deletion_policy"): DELETION_POLICY,
            Optional("retention_policy"): RETENTION_POLICY,
            Optional("versioning"): bool,
            Optional("lifecycle_rules"): [LIFECYCLE_RULE],
            Optional("data_migration"): DATA_MIGRATION,
        }
    },
}

S3_POLICY_DEFINITION = dict(S3_BASE)
S3_POLICY_DEFINITION.update({"type": "s3-policy"})

S3_DEFINITION = dict(S3_BASE)
S3_DEFINITION.update(
    {
        "type": "s3",
        Optional("objects"): [{"key": str, Optional("body"): str, Optional("content_type"): str}],
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

ALB_DEFINITION = {
    "type": "alb",
    Optional("environments"): {
        ENV_NAME: Or(
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

PROMETHEUS_POLICY_DEFINITION = {
    "type": "prometheus-policy",
    Optional("services"): Or("__all__", [str]),
    Optional("environments"): {
        ENV_NAME: {
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
        Optional("account"): str,
        Optional("branch", default="main"): str,
        Optional("pipeline_to_trigger"): str,
        Optional("versions"): _PIPELINE_VERSIONS_OVERRIDES,
        "slack_channel": str,
        "trigger_on_push": bool,
        "environments": {str: Or(None, _ENVIRONMENTS_PARAMS)},
    }
}

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
                REDIS_DEFINITION,
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


def validate_platform_config(config):
    PLATFORM_CONFIG_SCHEMA.validate(config)
    enriched_config = apply_environment_defaults(config)
    _validate_environment_pipelines(enriched_config)
    _validate_environment_pipelines_triggers(enriched_config)
    _validate_codebase_pipelines(enriched_config)
    validate_database_copy_section(enriched_config)

    _validate_extension_supported_versions(
        config=config,
        extension_type="redis",
        version_key="engine",
        get_supported_versions_fn=get_supported_redis_versions,
    )
    _validate_extension_supported_versions(
        config=config,
        extension_type="opensearch",
        version_key="engine",
        get_supported_versions_fn=get_supported_opensearch_versions,
    )


def _validate_extension_supported_versions(
    config, extension_type, version_key, get_supported_versions_fn
):
    extensions = config.get("extensions", {})
    if not extensions:
        return

    extensions_for_type = [
        extension
        for extension in config.get("extensions", {}).values()
        if extension.get("type") == extension_type
    ]

    supported_extension_versions = get_supported_versions_fn()
    extensions_with_invalid_version = []

    for extension in extensions_for_type:

        environments = extension.get("environments", {})

        if not isinstance(environments, dict):
            click.secho(
                "Error: Opensearch extension definition is invalid type, expected dictionary",
                fg="red",
            )
            continue
        for environment, env_config in environments.items():
            extension_version = env_config.get(version_key)
            if extension_version not in supported_extension_versions:
                extensions_with_invalid_version.append(
                    {"environment": environment, "version": extension_version}
                )

    for version_failure in extensions_with_invalid_version:
        click.secho(
            f"{extension_type} version for environment {version_failure['environment']} is not in the list of supported {extension_type} versions: {supported_extension_versions}. Provided Version: {version_failure['version']}",
            fg="red",
        )


def validate_database_copy_section(config):
    extensions = config.get("extensions", {})
    if not extensions:
        return

    postgres_extensions = {
        key: ext for key, ext in extensions.items() if ext.get("type", None) == "postgres"
    }

    if not postgres_extensions:
        return

    errors = []

    for extension_name, extension in postgres_extensions.items():
        database_copy_sections = extension.get("database_copy", [])

        if not database_copy_sections:
            return

        all_environments = [env for env in config.get("environments", {}).keys() if not env == "*"]
        all_envs_string = ", ".join(all_environments)

        for section in database_copy_sections:
            from_env = section["from"]
            to_env = section["to"]

            if from_env == to_env:
                errors.append(
                    f"database_copy 'to' and 'from' cannot be the same environment in extension '{extension_name}'."
                )

            if "prod" in to_env:
                errors.append(
                    f"Copying to a prod environment is not supported: database_copy 'to' cannot be '{to_env}' in extension '{extension_name}'."
                )

            if from_env not in all_environments:
                errors.append(
                    f"database_copy 'from' parameter must be a valid environment ({all_envs_string}) but was '{from_env}' in extension '{extension_name}'."
                )

            if to_env not in all_environments:
                errors.append(
                    f"database_copy 'to' parameter must be a valid environment ({all_envs_string}) but was '{to_env}' in extension '{extension_name}'."
                )

    if errors:
        abort_with_error("\n".join(errors))


def _validate_environment_pipelines(config):
    bad_pipelines = {}
    for pipeline_name, pipeline in config.get("environment_pipelines", {}).items():
        bad_envs = []
        pipeline_account = pipeline.get("account", None)
        if pipeline_account:
            for env in pipeline.get("environments", {}).keys():
                env_account = (
                    config.get("environments", {})
                    .get(env, {})
                    .get("accounts", {})
                    .get("deploy", {})
                    .get("name")
                )
                if not env_account == pipeline_account:
                    bad_envs.append(env)
        if bad_envs:
            bad_pipelines[pipeline_name] = {"account": pipeline_account, "bad_envs": bad_envs}
    if bad_pipelines:
        message = "The following pipelines are misconfigured:"
        for pipeline, detail in bad_pipelines.items():
            envs = detail["bad_envs"]
            acc = detail["account"]
            message += f"  '{pipeline}' - these environments are not in the '{acc}' account: {', '.join(envs)}\n"
        abort_with_error(message)


def _validate_codebase_pipelines(config):
    if CODEBASE_PIPELINES_KEY in config:
        for codebase in config[CODEBASE_PIPELINES_KEY]:
            codebase_environments = []

            for pipeline in codebase["pipelines"]:
                codebase_environments += [e["name"] for e in pipeline[ENVIRONMENTS_KEY]]

            unique_codebase_environments = sorted(list(set(codebase_environments)))

            if sorted(codebase_environments) != sorted(unique_codebase_environments):
                abort_with_error(
                    f"The {PLATFORM_CONFIG_FILE} file is invalid, each environment can only be "
                    "listed in a single pipeline per codebase"
                )


def _validate_environment_pipelines_triggers(config):
    errors = []
    pipelines_with_triggers = {
        pipeline_name: pipeline
        for pipeline_name, pipeline in config.get("environment_pipelines", {}).items()
        if "pipeline_to_trigger" in pipeline
    }

    for pipeline_name, pipeline in pipelines_with_triggers.items():
        pipeline_to_trigger = pipeline["pipeline_to_trigger"]
        if pipeline_to_trigger not in config.get("environment_pipelines", {}):
            message = f"  '{pipeline_name}' - '{pipeline_to_trigger}' is not a valid target pipeline to trigger"

            errors.append(message)
            continue

        if pipeline_to_trigger == pipeline_name:
            message = f"  '{pipeline_name}' - pipelines cannot trigger themselves"
            errors.append(message)

    if errors:
        error_message = "The following pipelines are misconfigured: \n"
        abort_with_error(error_message + "\n  ".join(errors))


def lint_yaml_for_duplicate_keys(file_path):
    lint_yaml_config = """
rules:
  key-duplicates: enable
"""
    yaml_config = config.YamlLintConfig(lint_yaml_config)

    with open(file_path, "r") as yaml_file:
        file_contents = yaml_file.read()
        results = linter.run(file_contents, yaml_config)

    parsed_results = [
        "\t" + f"Line {result.line}: {result.message}".replace(" in mapping (key-duplicates)", "")
        for result in results
    ]

    return parsed_results


def load_and_validate_platform_config(path=PLATFORM_CONFIG_FILE, disable_file_check=False):
    if not disable_file_check:
        config_file_check(path)
    try:
        conf = yaml.safe_load(Path(path).read_text())
        duplicate_keys = lint_yaml_for_duplicate_keys(path)
        if duplicate_keys:
            abort_with_error(
                "Duplicate keys found in platform-config:"
                + os.linesep
                + os.linesep.join(duplicate_keys)
            )
        validate_platform_config(conf)
        return conf
    except ParserError:
        abort_with_error(f"{PLATFORM_CONFIG_FILE} is not valid YAML")
    except SchemaError as e:
        abort_with_error(f"Schema error in {PLATFORM_CONFIG_FILE}. {e}")


def config_file_check(path=PLATFORM_CONFIG_FILE):
    platform_config_exists = Path(path).exists()
    errors = []
    warnings = []

    messages = {
        "storage.yml": {"instruction": " under the key 'extensions'", "type": errors},
        "extensions.yml": {"instruction": " under the key 'extensions'", "type": errors},
        "pipelines.yml": {
            "instruction": ", change the key 'codebases' to 'codebase_pipelines'",
            "type": errors,
        },
        PLATFORM_HELPER_VERSION_FILE: {
            "instruction": ", under the key `default_versions: platform-helper:`",
            "type": warnings,
        },
    }

    for file in messages.keys():
        if Path(file).exists():
            message = (
                f"`{file}` is no longer supported. Please move its contents into the "
                f"`{PLATFORM_CONFIG_FILE}` file{messages[file]['instruction']} and delete `{file}`."
            )
            messages[file]["type"].append(message)

    if not errors and not warnings and not platform_config_exists:
        errors.append(
            f"`{PLATFORM_CONFIG_FILE}` is missing. "
            "Please check it exists and you are in the root directory of your deployment project."
        )

    if warnings:
        click.secho("\n".join(warnings), bg="yellow", fg="black")
    if errors:
        click.secho("\n".join(errors), bg="red", fg="white")
        exit(1)


S3_SCHEMA = Schema(S3_DEFINITION)
S3_POLICY_SCHEMA = Schema(S3_POLICY_DEFINITION)
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
