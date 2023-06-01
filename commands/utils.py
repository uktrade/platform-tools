from pathlib import Path
import re

import boto3
import jinja2


SSM_BASE_PATH = "/copilot/{app}/{env}/secrets/"
SSM_PATH = "/copilot/{app}/{env}/secrets/{name}"


def mkdir(base, path):

    if (base / path).exists():
        return f"Directory {path} exists; doing nothing"

    (base / path).mkdir(parents=True)
    return f"Directory {path} created"


def mkfile(base, path, contents, overwrite=False):

    file_exists = (base / path).exists()

    if file_exists and not overwrite:
        return f"File {path} exists; doing nothing"

    action = "overwritten" if overwrite else "created"

    with open(base / path, "w") as fd:
        fd.write(contents)

    return f"File {path} {action}"


def camel_case(s):
    s = re.sub(r"(_|-)+", " ", s).title().replace(" ", "")
    return ''.join([s[0].lower(), s[1:]])


def set_ssm_param(app, env, param_name, param_value, overwrite, exists):
    client = boto3.client('ssm')
    args = dict(
        Name=param_name,
        Description='copied from cloudfoundry',
        Value=param_value,
        Type='SecureString',
        Overwrite=overwrite,
        Tags=[
                {
                    'Key': 'copilot-application',
                    'Value': app
                },
                {
                    'Key': 'copilot-environment',
                    'Value': env
                },
        ],
    )

    if overwrite and exists:
        # Tags can't be updated when overwriting
        del args["Tags"]

    response = client.put_parameter(**args)


def get_ssm_secret_names(app, env):
    client = boto3.client('ssm')

    path = SSM_BASE_PATH.format(app=app, env=env)

    params = dict(
        Path=path,
        Recursive=False,
        WithDecryption=True,
        MaxResults=10,
    )

    secret_names = []

    while True:
        response = client.get_parameters_by_path(
            **params
        )

        for secret in response["Parameters"]:
            secret_names.append(secret["Name"])

        if "NextToken" in response:
            params["NextToken"] = response["NextToken"]
        else:
            break

    return sorted(secret_names)


def setup_templates():
    template_path = Path(__file__).parent.parent / Path("templates")
    templateLoader = jinja2.FileSystemLoader(searchpath=template_path)
    templateEnv = jinja2.Environment(loader=templateLoader)

    templates = {
        "instructions": templateEnv.get_template("instructions.txt"),
        "storage-instructions": templateEnv.get_template("storage-instructions.txt"),
        "svc": {
            "public-manifest": templateEnv.get_template("svc/manifest-public.yml"),
            "backend-manifest": templateEnv.get_template("svc/manifest-backend.yml"),
            "opensearch": templateEnv.get_template("svc/addons/opensearch.yml"),
            "rds-postgres": templateEnv.get_template("svc/addons/rds-postgres.yml"),
            "aurora-postgres": templateEnv.get_template("svc/addons/aurora-postgres.yml"),
            "redis": templateEnv.get_template("svc/addons/redis.yml"),
            "s3": templateEnv.get_template("svc/addons/s3.yml"),
            "s3-policy": templateEnv.get_template("svc/addons/s3-policy.yml"),
        },
        "env": {
            "manifest": templateEnv.get_template("env/manifest.yml"),
            "opensearch": templateEnv.get_template("env/addons/opensearch.yml"),
            "rds-postgres": templateEnv.get_template("env/addons/rds-postgres.yml"),
            "aurora-postgres": templateEnv.get_template("env/addons/aurora-postgres.yml"),
            "redis": templateEnv.get_template("env/addons/redis-cluster.yml"),
            "s3": templateEnv.get_template("env/addons/s3.yml"),
        },
    }

    return templates
