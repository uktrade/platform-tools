#!/usr/bin/env python

'''
    Take all the files in ci-pipeline-config and combine into one document
'''

from collections import defaultdict
from pathlib import Path
import sys

import yaml


SOURCE_PATH = "../ci-pipeline-config/"

def import_ci_config():

    def _rename(k):
        return {
            "app": "paas-location",
            "environment": "environment",
            "vars": "vars",
        }[k]

    def _clean(env):

        return {
                _rename(k): v for k,v in env.items() if k not in ["type", "region", "run", "secrets", "vars"]
        }

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

    yaml.dump(config, sys.stdout)
