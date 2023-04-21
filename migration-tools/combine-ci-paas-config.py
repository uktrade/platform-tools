#!/usr/bin/env python

'''
    Take all the files in ci-pipeline-config and combine into one document
'''

from collections import defaultdict
from pathlib import Path
import sys

import yaml


CI_CONFIG_FILE = "ci-conf.yaml"
PAAS_CONFIG_FILE = "paas-conf.yaml"


if __name__ == "__main__":
    with open(CI_CONFIG_FILE, "r") as fd:
        ci = yaml.safe_load(fd)

    with open(PAAS_CONFIG_FILE, "r") as fd:
        paas = yaml.safe_load(fd)

    for namespace in ci["applications"]:
        if namespace == "shared":
            continue

        for app, data in ci["applications"][namespace].items():
            for env in data["environments"]:
                try:
                    env["paas"] = paas[env["paas-location"]]
                    #print("{} FOUND!".format(env["paas-location"]))
                except KeyError:
                    env["paas"] = "NO-APP-FOUND"
                    #print("{} MISSING CONFIG!".format(env["paas-location"]))

    # breakpoint()

    yaml.dump(ci, sys.stdout)
