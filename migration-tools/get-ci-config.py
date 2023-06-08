#!/usr/bin/env python

"""Take all the files in ci-pipeline-config and combine into one document."""

import os
from collections import defaultdict
from pathlib import Path

import yaml

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

    return namespaces


if __name__ == "__main__":
    config = import_ci_config()

    with open(f"{CURRENT_FILEPATH}/ci-config.yml", "w") as outfile:
        yaml.dump(config, outfile)
