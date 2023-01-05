#!/usr/bin/env python

from collections import defaultdict
from pathlib import Path
import re
import sys

import click
import jinja2
from schema import Optional, Schema, SchemaError
import yaml


config_schema = Schema({
    "app": str,
    "domain": str,
    "environments": {
        str: {
            Optional("certificate_arns"): [str]
        }
    },
    "services": [
        {
            "name": str,
            "repo": str,
            "image_location": str,
            "environments": {
                str: {
                    "ipfilter": bool,
                    "paas": str,
                    "url": str,
                }
            },
            "backing-services": [
                {
                    "name": str,
                    "type": lambda s: s in ("s3", "external-s3", "postgres", "redis", "opensearch",),
                    Optional("paas-description"): str,
                    Optional("paas-instance"): str,
                    Optional("notes"): str,
                    Optional("bucket_name"): str,           # for external-s3 type
                    Optional("readonly"): bool,             # for external-s3 type
                }
            ]
        }
    ],
})


def _mkdir(base, path):

    if (base / path).exists():
        return f"directory {path} exists; doing nothing"

    (base / path).mkdir(parents=True)
    return f"directory {path} created"


def _mkfile(base, path, contents):

    if (base / path).exists():
        return f"file {path} exists; doing nothing"

    with open(base / path, "w") as fd:
        fd.write(contents)
    return f"file {path} created"


def camel_case(s):
  s = re.sub(r"(_|-)+", " ", s).title().replace(" ", "")
  return ''.join([s[0].lower(), s[1:]])


@click.command()
@click.argument("filename", type=click.Path(exists=True))
@click.argument("output", type=click.Path(exists=True), default=".")
def main(filename, output):
    """
    Generate copilot boilerplate code

    FILENAME is the name of the input yaml config file
    OUTPUT is the location of the repo root dir. If not supplied, the current directory is used instead.
    """
    with open(filename, "r") as fd:
        conf = yaml.safe_load(fd)

    # validate the file
    schema = Schema(config_schema)
    data = schema.validate(conf)
    base_path = Path(output)

    env_template = templateEnv.get_template("env-manifest.yaml")
    svc_template = templateEnv.get_template("svc-manifest.yaml")
    instructions_template = templateEnv.get_template("instructions.txt")

    backing_service_templates ={
        "opensearch": templateEnv.get_template("addons/opensearch.yaml"),
        "postgres": templateEnv.get_template("addons/postgres.yaml"),
        "redis": templateEnv.get_template("addons/redis.yaml"),
        "s3": templateEnv.get_template("addons/s3.yaml"),
        "external-s3": templateEnv.get_template("addons/external-s3.yaml"),
    }

    click.echo("GENERATING COPILOT CONFIG FILES")

    # create copilot directory
    click.echo(_mkdir(base_path, "copilot"))

    # create copilot/.workspace file
    contents = "application: {}".format(data["app"])
    click.echo(_mkfile(base_path, "copilot/.workspace", contents))

    # create copilot/environments directory
    click.echo(_mkdir(base_path, "copilot/environments"))

    # create each environment diretory and manifest.yaml
    for name, env in data["environments"].items():
        click.echo(_mkdir(base_path, f"copilot/environments/{name}"))
        contents = env_template.render({
            "name": name,
            "certificate_arn": env["certificate_arns"][0] if "certificate_arns" in env else ""
        })
        click.echo(_mkfile(base_path, f"copilot/environments/{name}/manifest.yaml", contents))

    # create each service directory and manifest.yaml
    for service in data["services"]:
        name = service["name"]
        click.echo(_mkdir(base_path, f"copilot/{name}/addons/"))
        contents = svc_template.render(service)
        click.echo(_mkfile(base_path, f"copilot/{name}/manifest.yaml", contents))

        if service["backing-services"]:
            click.echo(_mkdir(base_path, "copilot"))

        for bs in service["backing-services"]:
            bs["prefix"] = camel_case(name + "-" + bs["name"])

            contents = backing_service_templates[bs["type"]].render(dict(service=bs))
            _mkfile(base_path, f"copilot/{name}/addons/{bs['name']}.yaml", contents)

    # generate instructions
    instructions = instructions_template.render(data)
    click.echo("---")
    click.echo(instructions)


if __name__ == "__main__":
    template_path = Path(__file__).parent / Path("templates")
    templateLoader = jinja2.FileSystemLoader(searchpath=template_path)
    templateEnv = jinja2.Environment(loader=templateLoader)

    main()
