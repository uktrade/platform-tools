import json
import sys
import os
import re
import subprocess
from argparse import ArgumentParser
from deepdiff import DeepDiff

allowed_resource_changes = {
    "aws_cloudfront_distribution": {
        "allowed_actions": ["update"],
        "allowed_attributes": [],
    },
    "aws_cloudfront_origin_access_control": {
        "allowed_actions": ["update", "no-op"],
        "allowed_attributes": ["name"]
    },
    "aws_acm_certificate": {
        "allowed_actions": ["update", "no-op"],
        "allowed_attributes": []
    },
    "aws_acm_certificate_validation": {
        "allowed_actions": ["create", "update", "no-op"],
        "allowed_attributes": []
    },
    "aws_route53_record": {
        "allowed_actions": ["update", "no-op"],
        "allowed_attributes": []
    }
}

allowed_tags = {
    "managed-by-repo",
    "managed-by"
}

def log(msg):
    print(msg, file=sys.stderr)

def run_command(command, working_dir) -> dict | str:
    log(f"Running command: {command}")

    try:
        command_result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=working_dir
        )
    except subprocess.CalledProcessError as e:
        log(f"Command failed: {command}")
        log(e.stderr.decode("utf-8"))
        sys.exit(1)

    try:
        return json.loads(command_result.stdout.decode("utf-8"))
    except json.decoder.JSONDecodeError:
        return command_result.stdout.decode("utf-8")

def review_tf_plan(tf_plan_data, allowList):
    resource_changes = tf_plan_data.get("resource_changes", [])

    if not resource_changes:
        print("No changes have been found in the plan.")
        return

    flagged_resources = []

    for resource in resource_changes:
        resource_address = resource.get("address")
        resource_type = resource.get("type")
        tf_operation = resource.get("change", {}).get("actions", [])

        if tf_operation == ["no-op"] or tf_operation == ["read"]:
            continue

        if resource_type not in allowList:
            flagged_resources.append({
                "address": resource_address,
                "type": resource_type,
                "actions": tf_operation,
                "reason": f"Resource type '{resource_type}' is not on the allow list."
            })
            continue

        rule = allowList[resource_type]
        allowed_actions = rule.get("allowed_actions", [])
        allowed_attributes = rule.get("allowed_attributes", [])

        blocked_actions = [action for action in tf_operation if action not in allowed_actions]

        if blocked_actions:
            flagged_resources.append({
                "address": resource_address,
                "type": resource_type,
                "actions": tf_operation,
                "reason": f"Action {blocked_actions} is not allowed to be performed."
            })
            continue

        if "update" in tf_operation:
            before_change = resource.get("change", {}).get("before") or {}
            after_change = resource.get("change", {}).get("after") or {}

            difference = DeepDiff(before_change, after_change, ignore_order=True)

            blocked_attributes = set()

            for changes in difference.values():
                if isinstance(changes, dict):
                    for path in changes.keys():
                        keys = re.findall(r"\['(.*?)'\]", path)

                        if not keys:
                            continue

                        top_level_attr = keys[0]

                        if top_level_attr == "tags":
                            continue

                        if top_level_attr == "tags_all":
                            if len(keys) > 1:
                                tag_name = keys[1]
                                if tag_name not in allowed_tags:
                                    blocked_attributes.add(f"tags_all['{tag_name}']")
                            else:
                                blocked_attributes.add("tags_all")
                            continue

                        if top_level_attr not in allowed_attributes:
                            blocked_attributes.add(top_level_attr)

            if blocked_attributes:
                flagged_resources.append({
                    "address": resource_address,
                    "type": resource_type,
                    "actions": tf_operation,
                    "reason": f"The change of attribute(s) {list(blocked_attributes)} is not allowed."
                })

    if flagged_resources:
        print("The following resources should be reviewed:\n")
        for item in flagged_resources:
            print(f"- Resource: {item['address']}")
            print(f"  Type: {item['type']}")
            print(f"  Planned Action: {item['actions']}")
            print(f"  Reason: {item['reason']}\n")

        sys.exit(1)
    else:
        print("No potential risk has been identified in the plan.")

if __name__ == "__main__":
    parser = ArgumentParser("tf_plan_checker")
    parser.add_argument("--working-dir", default=".", help="Directory containing Terraform code (default: current directory)")
    parser.add_argument("--init-args", default="", help="Extra arguments for terraform init (e.g. '-backend-config=\"key=...\"')")
    parser.add_argument("--plan-args", default="", help="Extra arguments for terraform plan (e.g. '-var-file=\"...\"')")
    parser.add_argument("--without-init", action='store_true', help="Skip terraform init")
    args = parser.parse_args()

    working_dir = args.working_dir
    temp_plan_file = "reviewer_temp.tfplan"

    if not os.path.isdir(working_dir):
        log(f"Error: Directory '{working_dir}' does not exist.")
        sys.exit(1)

    # Terraform Init
    if not args.without_init:
        init_cmd = f"terraform init {args.init_args}".strip()
        run_command(init_cmd, working_dir)

    # Terraform plan out
    plan_cmd = f"terraform plan -out={temp_plan_file} {args.plan_args}".strip()
    run_command(plan_cmd, working_dir)

    # Get the JSON of the plan
    show_cmd = f"terraform show -json {temp_plan_file}"
    plan_json_dict = run_command(show_cmd, working_dir)

    temp_plan_path = os.path.join(working_dir, temp_plan_file)
    if os.path.exists(temp_plan_path):
        os.remove(temp_plan_path)

    # Review the Plan
    review_tf_plan(plan_json_dict, allowed_resource_changes)