#!/usr/bin/env python

import copy
import json
from pathlib import Path

import boto3
import click
from jsonschema import validate as validate_json
import yaml

from .utils import camel_case, mkdir, mkfile, SSM_BASE_PATH, setup_templates


BASE_DIR = Path(__file__).parent.parent


@click.group()
def check():
    pass


@copilot.command()
@click.argument("service_name", type=str)
@click.argument("env", type=str, default="prod")
def get_service_secrets(service_name, env):
    """
    List secret names and values for a service
    """

    if not Path("./copilot").exists() or not Path("./copilot").is_dir():
        click.echo("Cannot find copilot directory. Run this command in the root of the deployment repository.")

    # is WAF configured?
    # is the CFN in `copilot/environments/addons` and `copilot/{service}/addons/` consistent with storage.yml?
    # is the IP filter enabled?
    # for each CFN file are all the keys under mappings occupied?
    # do services listed in copilot/services/ match storage.yaml

    # do envs listed in coipilot/evns match stoarge.yaml


if __name__ == "__main__":
    copilot()
