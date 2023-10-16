from pathlib import Path

import click
import yaml
from schema import Optional
from schema import Or
from schema import Schema

from dbt_copilot_helper.utils.validation import validate_string

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
        "environments": [
            {
                "name": str,
                Optional("requires_approval"): bool,
            },
        ],
    },
)


def load_and_validate_config(path, schema):
    with open(path, "r") as fd:
        conf = yaml.safe_load(fd)

    schema.validate(conf)

    return conf


def to_yaml(value):
    return yaml.dump(value, sort_keys=False)


def mkdir(base_path, directory_path):
    if (base_path / directory_path).exists():
        return f"Directory {directory_path} exists; doing nothing"

    (base_path / directory_path).mkdir(parents=True)
    return f"Directory {directory_path} created"


def mkfile(base_path, file_path, contents, overwrite=False):
    file_exists = (base_path / file_path).exists()

    if file_exists and not overwrite:
        return f"File {file_path} exists; doing nothing"

    action = "overwritten" if file_exists and overwrite else "created"

    with open(base_path / file_path, "w") as fd:
        fd.write(contents)

    return f"File {file_path} {action}"


def ensure_cwd_is_repo_root():
    """Exit if we're not in the root of the repo."""

    if not Path("./copilot").exists() or not Path("./copilot").is_dir():
        click.secho(
            "Cannot find copilot directory. Run this command in the root of the deployment repository.",
            bg="red",
        )
        exit(1)
