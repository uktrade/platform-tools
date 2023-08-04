#!/usr/bin/env python

"""Take all the files in ci-pipeline-config and combine into one document."""

import copy
import os
from collections import defaultdict

import yaml

CURRENT_FILEPATH = os.path.dirname(os.path.realpath(__file__))
SOURCE_PATH = f"{CURRENT_FILEPATH}/full-config.yml"


def detect_service_type(service):
    if "redis" in service["name"] or service["instance"][-4:] in ["-3.2", "-5.x", "-6.x"]:
        return "redis"

    if "postgres" in service["name"] or "postgres" in service["description"].lower():
        return "postgres"

    if "mysql" in service["description"].lower():
        return "mysql"

    if service["instance"].endswith("-1"):
        return "opensearch"

    if "S3" in service["description"]:
        return "s3"

    if service["instance"].endswith("-1.x"):
        return "influxdb"

    if (
        "log" in service["name"]
        or "autoscaler" in service["name"]
        or "ip-filter" in service["name"]
        or "autoscaler" in service["instance"]
        or "drain" in service["name"]
    ):
        return False

    return "!!UNKNOWN!!"


def space_to_copilot_app(app_name, ns_conf):
    envs = [env["environment"] for _, app in ns_conf.items() for env in app["environments"]]

    app_config = {
        "app": app_name,
        "environments": {k: {} for k in envs},
        "services": [],
    }

    backing_services = defaultdict(dict)
    secrets = defaultdict(list)

    for service, service_conf in ns_conf.items():
        for environment in service_conf["environments"]:
            if "paas" in environment and isinstance(environment["paas"], dict):
                secrets[service].extend(environment["paas"]["env_keys"])
                for bs in environment["paas"]["services"]:
                    if bs["name"] not in backing_services[environment["environment"]]:
                        backing_services[environment["environment"]][bs["name"]] = []
                    backing_services[environment["environment"]][bs["name"]].append(service)

        env_keys = sorted(list(set(secrets[service])))
        secrets[service] = dict(zip(env_keys, env_keys))

    for service, service_conf in ns_conf.items():
        if "ip-filter" in service:
            continue

        other_secrets = set([sx for sn, sv in secrets.items() for sx in sv if sn != service])
        svc_secrets = set(secrets[service].keys())
        overlapping_secrets = svc_secrets.intersection(other_secrets)

        processes = None
        for env_conf in service_conf["environments"]:
            if "paas" not in env_conf or env_conf["paas"] == "NO-APP-FOUND":
                continue
            processes = env_conf["paas"]["processes"]

        if not processes:
            continue

        web_processes = [p for p in processes if p["type"] == "web"]
        other_proceses = [p for p in processes if p["type"] != "web"]

        svc = {
            "name": service,
            "type": "public",
            "repo": service_conf["scm"],
            "image_location": "public.ecr.aws/uktrade/copilot-bootstrap:latest",
            "environments": {},
            "secrets": secrets[service],
            "env_vars": {},
        }

        if overlapping_secrets:
            svc["overlapping_secrets"] = sorted(list(overlapping_secrets))

        for environment in service_conf["environments"]:
            if isinstance(environment["paas"], dict):
                ipfilter = False
                url = None
                for route in environment["paas"]["routes"]:
                    if route["internal"]:
                        continue

                    ipfilter = ipfilter or route["ipfilter"]

                    if route["host"]:
                        url = f"{route['host']}.{route['domain']}"
                    else:
                        url = route["domain"]

                    if "certificate_arns" in app_config["environments"][environment["environment"]]:
                        app_config["environments"][environment["environment"]]["certificate_arns"].append(
                            f"ACM-ARN-FOR-{url}",
                        )
                    else:
                        app_config["environments"][environment["environment"]]["certificate_arns"] = [
                            f"ACM-ARN-FOR-{url}",
                        ]

                svc["environments"][environment["environment"]] = {
                    "url": url,
                    "paas": environment["paas-location"],
                    "ipfilter": ipfilter,
                }

        app_config["services"].append(svc)

        for process in other_proceses:
            psvc = copy.deepcopy(svc)
            psvc["secrets_from"] = svc["name"]
            psvc["name"] += "-" + process["type"]
            psvc["type"] = "backend"
            psvc[
                "notes"
            ] = f"service created based on Procfile entry for {svc['name']} and will require access to the same backing services"

            if "overlapping_secrets" in psvc:
                del psvc["overlapping_secrets"]
            psvc["secrets"] = {}

            for env_name, env_conf in psvc["environments"].items():
                del env_conf["url"]
                del env_conf["ipfilter"]

            app_config["services"].append(psvc)

    return app_config


if __name__ == "__main__":
    folder = f"{CURRENT_FILEPATH}/../bootstrap-config"

    for filename in os.listdir(folder):
        os.remove(f"{folder}/{filename}")

    with open(SOURCE_PATH, "r") as fd:
        conf = yaml.safe_load(fd)

    for app_name, ns_conf in conf["applications"].items():
        print(app_name)
        app_conf = space_to_copilot_app(app_name, ns_conf)

        with open(f"{folder}/{app_name}-copilot.yml", "w") as fd:
            yaml.dump(app_conf, fd)
