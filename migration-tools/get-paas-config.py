#!/usr/bin/env python
import os
from collections import defaultdict
from pathlib import Path

import yaml
from cloudfoundry_client.client import CloudFoundryClient

CURRENT_FILEPATH = os.path.dirname(os.path.realpath(__file__))
SOURCE_PATH = f"{CURRENT_FILEPATH}/../../ci-pipeline-config/"


def import_ci_config():
    def _rename(k):
        return {
            "app": "paas-location",
            "environment": "environment",
            "vars": "vars",
        }[k]

    def _clean(env):
        return {_rename(k): v for k, v in env.items() if k not in ["type", "region", "run", "secrets", "vars"]}

    path = Path(SOURCE_PATH)

    namespaces = defaultdict(dict)

    for fl_path in path.glob("*.y*ml"):
        with open(fl_path, "r") as raw:
            conf = yaml.safe_load(raw)

            conf["environments"] = [_clean(env) for env in conf["environments"]]

        namespaces[conf["namespace"]][conf["name"]] = conf

        del conf["name"]
        del conf["namespace"]

    return namespaces


def get_paas_data(client):
    apps = {}

    for org in client.v2.organizations:
        print(f"Organisation: {org['entity']['name']}")
        for space in org.spaces():
            print(f"└── Space: {space['entity']['name']}")
            for app in space.apps():
                print(f"    ├── {app['entity']['name']}")
                env_keys = list(app["entity"]["environment_json"].keys()) if app["entity"]["environment_json"] else []

                env_keys = [k for k in env_keys if k not in ["GIT_COMMIT", "GIT_BRANCH"]]

                app_data = {
                    "services": [],
                    "routes": [],
                    "env_keys": env_keys,
                    "processes": [],
                }

                key_ = "{}/{}/{}".format(org["entity"]["name"], space["entity"]["name"], app["entity"]["name"])

                # get processes

                v3app = client.v3.apps.get(app["metadata"]["guid"])

                for process in v3app.processes():
                    proc = client.v3.processes.get(process["guid"])
                    app_data["processes"].append(
                        {
                            "type": proc["type"],
                            "command": proc["command"],
                        }
                    )

                for route in app.routes():
                    domain = route.domain()

                    internal = domain["entity"].get("internal", False)

                    route_data = {
                        "domain": domain["entity"]["name"],
                        "internal": internal,
                        "host": route["entity"]["host"],
                        "path": route["entity"]["path"],
                        "ipfilter": hasattr(route, "service_instance"),
                    }

                    app_data["routes"].append(route_data)

                for sb in app.service_bindings():
                    service = sb.service_instance()

                    if service["entity"]["name"] in ["log-drain", "autoscaler"]:
                        continue

                    service_data = {
                        "name": service["entity"]["name"],
                        "instance": "EMPTY",
                        "description": "EMPTY",
                    }

                    try:
                        plan = service.service_plan()

                        service_data["instance"] = plan["entity"]["name"]
                        service_data["description"] = plan["entity"]["description"]
                    except:
                        pass

                    app_data["services"].append(service_data)

                apps[key_] = app_data
    return apps


if __name__ == "__main__":
    config = import_ci_config()

    # you must authenticate via cli first!
    client = CloudFoundryClient.build_from_cf_config()

    paas_apps = get_paas_data(client)

    with open(f"{CURRENT_FILEPATH}/paas-config.yml", "w") as outfile:
        yaml.dump(paas_apps, outfile)
