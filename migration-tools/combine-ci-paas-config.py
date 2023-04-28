#!/usr/bin/env python

"""
    Take all the files in ci-pipeline-config and combine into one document
"""

import os

import yaml

CURRENT_FILEPATH = os.path.dirname(os.path.realpath(__file__))
CI_CONFIG_FILE = f"{CURRENT_FILEPATH}/ci-conf.yaml"
PAAS_CONFIG_FILE = f"{CURRENT_FILEPATH}/paas-config.yml"


if __name__ == "__main__":
    with open(CI_CONFIG_FILE, "r") as fd:
        ci = yaml.safe_load(fd)

    with open(PAAS_CONFIG_FILE, "r") as fd:
        paas = yaml.safe_load(fd)

    for namespace in ci["applications"]:
        if namespace == "shared":
            continue

        for app, data in ci["applications"][namespace].items():
            print(app)
            for env in data["environments"]:
                try:
                    env["paas"] = paas[env["paas-location"]]
                    #print("{} FOUND!".format(env["paas-location"]))
                except KeyError:
                    env["paas"] = "NO-APP-FOUND"
                    #print("{} MISSING CONFIG!".format(env["paas-location"]))

    # breakpoint()

    with open(f"{CURRENT_FILEPATH}/full-config.yml", 'w') as outfile:
        yaml.dump(ci, outfile)
