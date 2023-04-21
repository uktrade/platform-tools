#!/usr/bin/env python

'''
    Take all the files in ci-pipeline-config and combine into one document
'''

from collections import defaultdict
import copy
from pathlib import Path
import sys

import yaml

SOURCE_PATH = "full-config.yaml"


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

    if "log" in service["name"] or "autoscaler" in service["name"] or "ip-filter" in service["name"] or "autoscaler" in service["instance"] or "drain" in service["name"]:
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
    overlapping_secrets = defaultdict(list)
    for service, service_conf in ns_conf.items():

        for environment in service_conf["environments"]:
            if isinstance(environment["paas"], dict):
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
            if env_conf["paas"] == "NO-APP-FOUND":
                continue
            processes = env_conf["paas"]["processes"]

        if not processes:
            continue

        web_processes = [p for p in processes if p["type"] == "web" ]
        if len(web_processes) != 1:
            breakpoint()
        other_proceses = [p for p in processes if p["type"] != "web"]

        svc = {
            "name": service,
            "type": "public",
            "repo": service_conf["scm"],
            "image_location": "public.ecr.aws/uktrade/copilot-bootstrap:latest",
            "environments": {},
            #"backing-services": [],
            "secrets": secrets[service],
            "env_vars": {},
            #"command": web_processes[0]["command"]
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

                    # if environment["paas-location"].split("/")[0] in ["dit-services", "traderemedies-services"] and "gov.uk" in route["domain"]:
                    if route["host"]:
                        url = "{}.{}".format(route["host"], route["domain"])
                    else:
                        url = route["domain"]

                    if "certificate_arns" in app_config["environments"][environment["environment"]]:
                        app_config["environments"][environment["environment"]]["certificate_arns"].append(f"ACM-ARN-FOR-{url}")
                    else:
                        app_config["environments"][environment["environment"]]["certificate_arns"] = [f"ACM-ARN-FOR-{url}"]

                # if not url:
                #     url = environment["environment"] + "." + svc["name"] + "." + app_config["domain"]

                svc["environments"][environment["environment"]] = {
                    "url": url,
                    "paas": environment["paas-location"],
                    "ipfilter": ipfilter,
                }

                # Don't bother with missing keys.  Instead we can just fill in missing params
                # env_keys = set(environment["paas"]["env_keys"])
                # service_keys = set(svc["secrets"].keys())
                # if env_keys != service_keys:
                #     missing_keys = service_keys.difference(env_keys)
                #
                #     svc["environments"][environment["environment"]]["missing_env_keys"] = list(missing_keys)

                # NOTE: since adding storage.yaml w
                # for bs in environment["paas"]["services"]:
                #     if len(backing_services[environment["environment"]][bs["name"]]) > 1:
                #         note = "WARNING: shared between apps: " + " and ".join(backing_services[environment["environment"]][bs["name"]])
                #     else:
                #         note = ""

                #     svc["backing-services"].append({
                #         "type": detect_service_type(bs),
                #         "name": bs["name"],
                #         "paas-description": bs["description"],
                #         "paas-instance": bs["instance"],
                #         "notes": note,
                #     })

        app_config["services"].append(svc)

        for process in other_proceses:
            psvc = copy.deepcopy(svc)
            psvc["secrets_from"] = svc["name"]
            psvc["name"] += "-" + process["type"]
            psvc["type"] = "backend"
            #psvc["command"] = process["command"]
            psvc["notes"] = f"service created based on Procfile entry for {svc['name']} and will require access to the same backing services"

            if "overlapping_secrets" in psvc:
                del psvc["overlapping_secrets"]
            psvc["secrets"] = {}
            #psvc["backing-services"] = []

            for env_name, env_conf in psvc["environments"].items():
                del env_conf["url"]
                del env_conf["ipfilter"]

            app_config["services"].append(psvc)

    return app_config

if __name__ == "__main__":
    with open(SOURCE_PATH, "r") as fd:
        conf = yaml.safe_load(fd)

    for app_name, ns_conf in conf["applications"].items():
        app_conf = space_to_copilot_app(app_name, ns_conf)

        with open(app_name + "-copilot.yaml", "w") as fd:
            yaml.dump(app_conf, fd)
