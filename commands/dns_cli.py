#!/usr/bin/env python

import os
import time
from typing import Tuple

import click
import yaml
from boto3 import Session

from .utils import check_aws_conn
from .utils import check_response
from .utils import ensure_cwd_is_repo_root

# To do
# -----
# Check user has logged into the aws accounts before scanning the accounts
# When adding records from parent to subdomain, if ok, it then should remove them from parent domain
# (run a test before removing)

# Base domain depth
MAX_DOMAIN_DEPTH = 2
AWS_CERT_REGION = "eu-west-2"


def wait_for_certificate_validation(acm_client, certificate_arn, sleep_time=5, timeout=600):
    click.secho("waiting for cert...", fg="yellow")
    status = acm_client.describe_certificate(CertificateArn=certificate_arn)["Certificate"]["Status"]
    elapsed_time = 0
    while status == "PENDING_VALIDATION":
        if elapsed_time > timeout:
            raise Exception(f"Timeout ({timeout}s) reached for certificate validation")
        click.echo(
            click.style(f"{certificate_arn}", fg="white", bold=True)
            + click.style(f": Waiting {sleep_time}s for validation, {elapsed_time}s elapsed...", fg="yellow"),
        )
        time.sleep(sleep_time)
        status = acm_client.describe_certificate(CertificateArn=certificate_arn)["Certificate"]["Status"]
        elapsed_time += sleep_time
    click.secho("cert validated...", fg="green")


def create_cert(client, domain_client, domain, base_len):
    # Check if cert is present.
    arn = ""
    resp = client.list_certificates(
        CertificateStatuses=[
            "PENDING_VALIDATION",
            "ISSUED",
            "INACTIVE",
            "EXPIRED",
            "VALIDATION_TIMED_OUT",
            "REVOKED",
            "FAILED",
        ],
        MaxItems=500,
    )

    # Need to check if cert status is issued, if pending need to update dns
    for cert in resp["CertificateSummaryList"]:
        if domain == cert["DomainName"]:
            click.secho("Cert already exists, do not need to create.", fg="green")
            return cert["CertificateArn"]

    if not click.confirm(
        click.style("Creating Cert for ", fg="yellow")
        + click.style(f"{domain}\n", fg="white", bold=True)
        + click.style("Do you want to continue?", fg="yellow"),
    ):
        exit()

    parts = domain.split(".")

    # We only want to create domains max 2 deep so remove all sub domains in excess
    parts_to_remove = len(parts) - base_len - MAX_DOMAIN_DEPTH
    domain_to_create = ".".join(parts[parts_to_remove:]) + "."
    click.secho(domain_to_create, fg="yellow")
    # cert_client = DNSValidatedACMCertClient(domain=domain, profile='intranet')
    response = client.request_certificate(DomainName=domain, ValidationMethod="DNS")

    arn = response["CertificateArn"]

    # Create DNS validation records
    # Need a pause for it to populate the DNS resource records
    response = client.describe_certificate(CertificateArn=arn)
    while (
        response["Certificate"].get("DomainValidationOptions") is None
        or response["Certificate"]["DomainValidationOptions"][0].get("ResourceRecord") is None
    ):
        click.secho("Waiting for DNS records...", fg="yellow")
        time.sleep(2)
        response = client.describe_certificate(CertificateArn=arn)

    cert_record = response["Certificate"]["DomainValidationOptions"][0]["ResourceRecord"]
    response = domain_client.list_hosted_zones_by_name()

    for hz in response["HostedZones"]:
        if hz["Name"] == domain_to_create:
            domain_id = hz["Id"]
            break

    # Add NS records of subdomain to parent
    click.secho(domain_id, fg="yellow")

    if not click.confirm(
        click.style("Updating DNS record for cert ", fg="yellow")
        + click.style(f"{domain}\n", fg="white", bold=True)
        + click.style("Do you want to continue?", fg="yellow"),
    ):
        exit()

    response = domain_client.change_resource_record_sets(
        HostedZoneId=domain_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "CREATE",
                    "ResourceRecordSet": {
                        "Name": cert_record["Name"],
                        "Type": cert_record["Type"],
                        "TTL": 300,
                        "ResourceRecords": [
                            {"Value": cert_record["Value"]},
                        ],
                    },
                },
            ],
        },
    )

    # Wait for certificate to get to validation state before continuing
    wait_for_certificate_validation(client, certificate_arn=arn, sleep_time=5, timeout=600)

    return arn


def add_records(client, records, subdom_id, action):
    if records["Type"] == "A":
        response = client.change_resource_record_sets(
            HostedZoneId=subdom_id,
            ChangeBatch={
                "Comment": "Record created for copilot",
                "Changes": [
                    {
                        "Action": action,
                        "ResourceRecordSet": {
                            "Name": records["Name"],
                            "Type": records["Type"],
                            "AliasTarget": {
                                "HostedZoneId": records["AliasTarget"]["HostedZoneId"],
                                "DNSName": records["AliasTarget"]["DNSName"],
                                "EvaluateTargetHealth": records["AliasTarget"]["EvaluateTargetHealth"],
                            },
                        },
                    },
                ],
            },
        )
    else:
        response = client.change_resource_record_sets(
            HostedZoneId=subdom_id,
            ChangeBatch={
                "Comment": "Record created for copilot",
                "Changes": [
                    {
                        "Action": action,
                        "ResourceRecordSet": {
                            "Name": records["Name"],
                            "Type": records["Type"],
                            "TTL": records["TTL"],
                            "ResourceRecords": [
                                {"Value": records["ResourceRecords"][0]["Value"]},
                            ],
                        },
                    },
                ],
            },
        )

    check_response(response)
    click.echo(
        click.style(f"{records['Name']}, Type: {records['Type']}", fg="white", bold=True)
        + click.style("Added.", fg="magenta"),
    )
    return response["ChangeInfo"]["Status"]


def check_for_records(client, parent_id, subdom, subdom_id):
    records_to_add = []
    response = client.list_resource_record_sets(
        HostedZoneId=parent_id,
    )

    for records in response["ResourceRecordSets"]:
        if subdom in records["Name"]:
            click.secho(records["Name"] + " found", fg="green")
            records_to_add.append(records)
            add_records(client, records, subdom_id)
    return True


def create_hosted_zone(client, domain, start_domain, base_len):
    parts = domain.split(".")

    # We only want to create domains max 2 deep so remove all sub domains in excess
    parts_to_remove = len(parts) - base_len - MAX_DOMAIN_DEPTH
    domain_to_create = parts[parts_to_remove:]

    # Walk back domain name
    for x in reversed(range(len(domain_to_create) - (len(start_domain.split(".")) - 1))):
        subdom = ".".join(domain_to_create[(x):]) + "."

        if not click.confirm(
            click.style("About to create domain: ", fg="cyan")
            + click.style(f"{subdom}\n", fg="white", bold=True)
            + click.style("Do you want to continue?", fg="cyan"),
        ):
            exit()

        parent = ".".join(subdom.split(".")[1:])
        response = client.list_hosted_zones_by_name()

        for hz in response["HostedZones"]:
            if hz["Name"] == parent:
                parent_id = hz["Id"]
                break

        # update CallerReference to unique string eg date.
        response = client.create_hosted_zone(
            Name=subdom,
            CallerReference=f"{subdom}_from_code",
        )
        ns_records = response["DelegationSet"]
        subdom_id = response["HostedZone"]["Id"]

        # Check if records existed in the parent domain, if so they need to be copied to sub domain.
        check_for_records(client, parent_id, subdom, subdom_id)

        if not click.confirm(
            click.style(f"Updating parent {parent} domain with records: ", fg="cyan")
            + click.style("{ns_records['NameServers']}\n", fg="white", bold=True)
            + click.style("Do you want to continue?", fg="cyan"),
        ):
            exit()

        # Add NS records of subdomain to parent
        nameservers = ns_records["NameServers"]
        # append  . to make fqdn
        nameservers = [f"{nameserver}." for nameserver in nameservers]
        nameserver_resource_records = [{"Value": nameserver} for nameserver in nameservers]

        response = client.change_resource_record_sets(
            HostedZoneId=parent_id,
            ChangeBatch={
                "Changes": [
                    {
                        "Action": "CREATE",
                        "ResourceRecordSet": {
                            "Name": subdom,
                            "Type": "NS",
                            "TTL": 300,
                            "ResourceRecords": nameserver_resource_records,
                        },
                    },
                ],
            },
        )

        return True


def check_r53(domain_session, project_session, domain, base_domain):
    # find the hosted zone
    domain_client = domain_session.client("route53")
    acm_client = project_session.client("acm", region_name=AWS_CERT_REGION)

    # create the certificate
    response = domain_client.list_hosted_zones_by_name()

    hosted_zones = {}
    for hz in response["HostedZones"]:
        hosted_zones[hz["Name"]] = hz

    # Check if base domain is valid
    if base_domain[-1] != ".":
        base_domain = base_domain + "."

    if base_domain not in hosted_zones:
        click.secho(
            f"The base domain: {base_domain} does not exist in your AWS domain account \
                {response['HostedZones']}",
            fg="red",
        )
        exit()

    base_len = len(base_domain.split(".")) - 1
    parts = domain.split(".")

    for _ in range(len(parts) - 1):
        subdom = ".".join(parts) + "."
        click.secho(f"Searching for {subdom}... ", fg="yellow")
        if subdom in hosted_zones:
            click.secho("Found hosted zone " + hosted_zones[subdom]["Name"], fg="green")

            # We only want to go 2 sub domains deep in R53
            if (len(parts) - base_len) < MAX_DOMAIN_DEPTH:
                click.secho("Creating Hosted Zone", fg="magenta")
                create_hosted_zone(domain_client, domain, subdom, base_len)

            break

        parts.pop(0)
    else:
        # This should only occur when base domain this needs is not found
        click.secho(f"Root Domain not found for {domain}", fg="red")
        return

    # add records to hosted zone to validate certificate
    cert_arn = create_cert(acm_client, domain_client, domain, base_len)

    return cert_arn


def get_load_balancer_domain_and_configuration(
    project_session: Session, app: str, svc: str, env: str
) -> Tuple[str, dict]:
    def separate_hyphenated_application_environment_and_service(
        hyphenated_string, number_of_items_of_interest, number_of_trailing_items
    ):
        # The application name may be hyphenated, so we start splitting
        # at the hyphen after the first item of interest and return the
        # items of interest only...
        return hyphenated_string.rsplit("-", number_of_trailing_items + number_of_items_of_interest - 1)[
            :number_of_items_of_interest
        ]

    proj_client = project_session.client("ecs")

    response = proj_client.list_clusters()
    check_response(response)
    no_items = True
    for cluster_arn in response["clusterArns"]:
        cluster_name = cluster_arn.split("/")[1]
        cluster_app, cluster_env = separate_hyphenated_application_environment_and_service(cluster_name, 2, 2)
        if cluster_app == app and cluster_env == env:
            no_items = False
            break

    if no_items:
        click.echo(
            click.style("There are no clusters matching ", fg="red")
            + click.style(f"{app} ", fg="white", bold=True)
            + click.style("in this aws account", fg="red"),
        )
        exit()

    response = proj_client.list_services(cluster=cluster_name)
    check_response(response)
    no_items = True
    for service_arn in response["serviceArns"]:
        fully_qualified_service_name = service_arn.split("/")[2]
        service_app, service_env, service_name = separate_hyphenated_application_environment_and_service(
            fully_qualified_service_name, 3, 2
        )
        if service_app == app and service_env == env and service_name == svc:
            no_items = False
            break

    if no_items:
        click.echo(
            click.style("There are no services matching ", fg="red")
            + click.style(f"{svc}", fg="white", bold=True)
            + click.style(" in this aws account", fg="red"),
        )
        exit()

    elb_client = project_session.client("elbv2")

    elb_arn = elb_client.describe_target_groups(
        TargetGroupArns=[
            proj_client.describe_services(
                cluster=cluster_name,
                services=[
                    fully_qualified_service_name,
                ],
            )["services"][
                0
            ]["loadBalancers"][0]["targetGroupArn"],
        ],
    )["TargetGroups"][0]["LoadBalancerArns"][0]

    response = elb_client.describe_load_balancers(LoadBalancerArns=[elb_arn])
    check_response(response)

    # Find the domain name
    with open(f"./copilot/{svc}/manifest.yml", "r") as fd:
        conf = yaml.safe_load(fd)
        if "environments" in conf:
            for domain in conf["environments"].items():
                if domain[0] == env:
                    domain_name = domain[1]["http"]["alias"]

        # What happens if domain_name isn't set? Should we raise an error? Return default ? Or None?

    return domain_name, response["LoadBalancers"][0]


@click.group()
def domain():
    pass


@domain.command()
@click.option("--domain-profile", help="aws account profile name for R53 domains account", required=True)
@click.option("--project-profile", help="aws account profile name for certificates account", required=True)
@click.option("--base-domain", help="root domain", required=True)
def check_domain(domain_profile, project_profile, base_domain):
    """Scans to see if Domain exists."""

    path = "copilot"

    domain_session = check_aws_conn(domain_profile)
    project_session = check_aws_conn(project_profile)

    if not os.path.exists(path):
        click.secho("Please check path, manifest file not found", fg="red")
        exit()

    if path.split(".")[-1] == "yml" or path.split(".")[-1] == "yaml":
        click.secho("Please do not include the filename in the path", fg="red")
        exit()

    cert_list = {}
    for root, dirs, files in os.walk(path):
        for file in files:
            if file == "manifest.yml" or file == "manifest.yaml":
                # Need to check that the manifest file is correctly configured.
                with open(os.path.join(root, file), "r") as fd:
                    conf = yaml.safe_load(fd)
                    if "environments" in conf:
                        click.echo(
                            click.style("Checking file: ", fg="cyan")
                            + click.style(os.path.join(root, file), fg="white"),
                        )
                        click.secho("Domains listed in manifest file", fg="cyan", underline=True)

                        for env, domain in conf["environments"].items():
                            click.secho("Environment: " + env + "\t=> Domain: " + domain["http"]["alias"], fg="yellow")
                            cert_arn = check_r53(domain_session, project_session, domain["http"]["alias"], base_domain)
                            cert_list.update({domain["http"]["alias"]: cert_arn})
    if cert_list:
        click.secho("\nHere are your Cert ARNs:", fg="cyan")
        for domain, cert in cert_list.items():
            click.secho(f"Domain: {domain}\t => Cert ARN: {cert}", fg="white", bold=True)
    else:
        click.secho("No domains found, please check the manifest file", fg="red")


@domain.command()
@click.option("--app", help="Application Name", required=True)
@click.option("--domain-profile", help="aws account profile name for R53 domains account", required=True)
@click.option("--project-profile", help="aws account profile name for application account", required=True)
@click.option("--svc", help="Service Name", required=True)
@click.option("--env", help="Environment", required=True)
def assign_domain(app, domain_profile, project_profile, svc, env):
    """Check R53 domain is pointing to the correct ECS Load Blanacer."""
    domain_session = check_aws_conn(domain_profile)
    project_session = check_aws_conn(project_profile)

    ensure_cwd_is_repo_root()

    # Find the Load Balancer name.
    domain_name, load_balancer_configuration = get_load_balancer_domain_and_configuration(
        project_session, app, svc, env
    )
    elb_name = load_balancer_configuration["DNSName"]

    click.echo(
        click.style("The Domain: ", fg="yellow")
        + click.style(f"{domain_name}\n", fg="white", bold=True)
        + click.style("has been assigned the Load Balancer: ", fg="yellow")
        + click.style(f"{elb_name}\n", fg="white", bold=True)
        + click.style("Checking to see if this is in R53", fg="yellow"),
    )

    domain_client = domain_session.client("route53")
    response = domain_client.list_hosted_zones_by_name()
    check_response(response)

    # Scan R53 Zone for matching domains and update records if needed.
    hosted_zones = {}
    for hz in response["HostedZones"]:
        hosted_zones[hz["Name"]] = hz

    parts = domain_name.split(".")
    for _ in range(len(parts) - 1):
        subdom = ".".join(parts) + "."
        click.echo(click.style("Searching for ", fg="yellow") + click.style(f"{subdom}..", fg="white", bold=True))

        if subdom in hosted_zones:
            click.echo(
                click.style("Found hosted zone ", fg="yellow")
                + click.style(hosted_zones[subdom]["Name"], fg="white", bold=True),
            )
            hosted_zone_id = hosted_zones[subdom]["Id"]

            # Does record existing
            response = domain_client.list_resource_record_sets(
                HostedZoneId=hosted_zone_id,
            )
            check_response(response)

            for record in response["ResourceRecordSets"]:
                if domain_name == record["Name"][:-1]:
                    click.echo(
                        click.style("Record: ", fg="yellow")
                        + click.style(f"{record['Name']} found", fg="white", bold=True),
                    )
                    click.echo(
                        click.style("is pointing to LB ", fg="yellow")
                        + click.style(f"{record['ResourceRecords'][0]['Value']}", fg="white", bold=True),
                    )
                    if record["ResourceRecords"][0]["Value"] != elb_name:
                        if click.confirm(
                            click.style("This doesnt match with the current LB ", fg="yellow")
                            + click.style(f"{elb_name}", fg="white", bold=True)
                            + click.style("Do you wish to update the record?", fg="yellow"),
                        ):
                            record = {
                                "Name": domain_name,
                                "Type": "CNAME",
                                "TTL": 300,
                                "ResourceRecords": [{"Value": elb_name}],
                            }
                            add_records(domain_client, record, hosted_zone_id, "UPSERT")
                    else:
                        click.secho("No need to add as it already exists", fg="green")
                    exit()

            record = {"Name": domain_name, "Type": "CNAME", "TTL": 300, "ResourceRecords": [{"Value": elb_name}]}

            if not click.confirm(
                click.style("Creating R53 record: ", fg="yellow")
                + click.style(f"{record['Name']} -> {record['ResourceRecords'][0]['Value']}\n", fg="white", bold=True)
                + click.style("In Domain: ", fg="yellow")
                + click.style(f"{subdom}", fg="white", bold=True)
                + click.style("\tZone ID: ", fg="yellow")
                + click.style(f"{hosted_zone_id}\n", fg="white", bold=True)
                + click.style("Do you want to continue?", fg="yellow"),
            ):
                exit()
            add_records(domain_client, record, hosted_zone_id, "CREATE")
            exit()

        parts.pop(0)

    else:
        click.echo(
            click.style("No hosted zone found for ", fg="yellow")
            + click.style(f"{domain_name}", fg="white", bold=True),
        )
        return


if __name__ == "__main__":
    domain()
