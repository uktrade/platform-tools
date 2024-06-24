#!/usr/bin/env python

import os
import re
import time
from pathlib import Path

import click
import yaml

from dbt_platform_helper.utils.aws import check_response
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.aws import get_load_balancer_configuration
from dbt_platform_helper.utils.aws import get_load_balancer_domain_and_configuration
from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.messages import abort_with_error
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)

# To do
# -----
# Check user has logged into the aws accounts before scanning the accounts
# When adding records from parent to subdomain, if ok, it then should remove them from parent domain
# (run a test before removing)

# Base domain depth
AVAILABLE_DOMAINS = {
    "great.gov.uk": "live",
    "trade.gov.uk": "live",
    "prod.uktrade.digital": "live",
    "uktrade.digital": "dev",
}
AWS_CERT_REGION = "eu-west-2"
COPILOT_DIR = "copilot"


def _wait_for_certificate_validation(acm_client, certificate_arn, sleep_time=10, timeout=600):
    click.secho(f"Waiting up to {timeout} seconds for certificate to be validated...", fg="yellow")
    status = acm_client.describe_certificate(CertificateArn=certificate_arn)["Certificate"][
        "Status"
    ]
    elapsed_time = 0
    while status == "PENDING_VALIDATION":
        if elapsed_time >= timeout:
            raise Exception(
                f"Timeout ({timeout}s) reached for certificate validation, might be worth checking things in the AWS Console"
            )
        click.echo(
            click.style(f"{certificate_arn}", fg="white", bold=True)
            + click.style(
                f": Waiting {sleep_time}s for validation, {elapsed_time}s elapsed, {timeout - elapsed_time}s until we give up...",
                fg="yellow",
            ),
        )
        time.sleep(sleep_time)
        status = acm_client.describe_certificate(CertificateArn=certificate_arn)["Certificate"][
            "Status"
        ]
        elapsed_time += sleep_time

    if status == "ISSUED":
        click.secho("Certificate validated...", fg="green")
    else:
        raise Exception(f"""Certificate validation failed with the status "{status}".""")


def create_cert(client, domain_client, domain_name, zone_id):
    certificate_arn = _get_existing_cert_if_one_exists_and_cleanup_bad_certs(client, domain_name)

    if certificate_arn:
        return certificate_arn

    if not click.confirm(
        click.style("Creating Certificate for ", fg="yellow")
        + click.style(f"{domain_name}\n", fg="white", bold=True)
        + click.style("Do you want to continue?", fg="yellow"),
    ):
        exit()

    certificate_arn = _request_cert(client, domain_name)

    # Create DNS validation records
    cert_record = _get_certificate_record(certificate_arn, client)

    if not click.confirm(
        click.style("Updating DNS record for certificate ", fg="yellow")
        + click.style(f"{domain_name}", fg="white", bold=True)
        + click.style(" with value ", fg="yellow")
        + click.style(f"""{cert_record["Value"]}\n""", fg="white", bold=True)
        + click.style("Do you want to continue?", fg="yellow"),
    ):
        exit()

    _create_resource_records(cert_record, domain_client, zone_id)

    # Wait for certificate to get to validation state before continuing.
    # Will upped the timeout from 600 to 1200 because he repeatedly saw it timeout at 600
    # and wants to give it a chance to take longer in case that's all that's wrong.
    _wait_for_certificate_validation(client, certificate_arn=certificate_arn, timeout=1200)

    return certificate_arn


def _get_existing_cert_if_one_exists_and_cleanup_bad_certs(client, domain):
    for cert in _certs_for_domain(client, domain):
        if cert["Status"] == "ISSUED":
            click.secho("Certificate already exists, do not need to create.", fg="green")
            return cert["CertificateArn"]
        else:
            click.secho(
                f"Certificate already exists but appears to be invalid (in status '{cert['Status']}'), deleting the old cert.",
                fg="yellow",
            )
            client.delete_certificate(CertificateArn=cert["CertificateArn"])
    return None


def _create_resource_records(cert_record, domain_client, zone_id):
    resource_records = domain_client.list_resource_record_sets(HostedZoneId=zone_id)[
        "ResourceRecordSets"
    ]

    for record in resource_records:
        if record["Type"] == cert_record["Type"] and record["Name"] == cert_record["Name"]:
            return

    domain_client.change_resource_record_sets(
        HostedZoneId=zone_id,
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


def _certs_for_domain(client, domain):
    # Check if cert is present.
    cert_list = client.list_certificates(
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
    )["CertificateSummaryList"]
    certs_for_domain = [cert for cert in cert_list if cert["DomainName"] == domain]
    return certs_for_domain


def _get_certificate_record(arn, client):
    # Need a pause for it to populate the DNS resource records
    cert_description = client.describe_certificate(CertificateArn=arn)
    while (
        cert_description["Certificate"].get("DomainValidationOptions") is None
        or cert_description["Certificate"]["DomainValidationOptions"][0].get("ResourceRecord")
        is None
    ):
        click.secho("Waiting for DNS records...", fg="yellow")
        time.sleep(2)
        cert_description = client.describe_certificate(CertificateArn=arn)
    return cert_description["Certificate"]["DomainValidationOptions"][0]["ResourceRecord"]


def _request_cert(client, domain):
    cert_response = client.request_certificate(DomainName=domain, ValidationMethod="DNS")
    arn = cert_response["CertificateArn"]
    return arn


def add_records(client, records, subdomain_id, action):
    if records["Type"] == "A":
        response = client.change_resource_record_sets(
            HostedZoneId=subdomain_id,
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
                                "EvaluateTargetHealth": records["AliasTarget"][
                                    "EvaluateTargetHealth"
                                ],
                            },
                        },
                    },
                ],
            },
        )
    else:
        response = client.change_resource_record_sets(
            HostedZoneId=subdomain_id,
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


def copy_records_from_parent_to_subdomain(client, parent_zone_id, subdomain, zone_id):
    response = client.list_resource_record_sets(HostedZoneId=parent_zone_id)

    for records in response["ResourceRecordSets"]:
        if subdomain in records["Name"]:
            click.secho(records["Name"] + " found", fg="green")
            add_records(client, records, zone_id, "UPSERT")


def create_hosted_zones(client, base_domain, subdomain):
    domains_to_create = get_required_subdomains(base_domain, subdomain)
    zone_ids = {}

    for domain_name in domains_to_create:
        domain_zone = f"{domain_name}."
        parent_domain = domain_name.split(".", maxsplit=1)[1]
        parent_zone = f"{parent_domain}."

        domain_zone_id, parent_zone_id = _get_paginated_zones(client, parent_zone, domain_zone)

        if parent_zone_id is None:
            click.secho(
                f"The hosted zone: {parent_zone} does not exist in your AWS domain account",
                fg="red",
            )
            exit()

        if domain_zone_id is not None:
            click.secho(f"Hosted zone '{domain_zone}' already exists", fg="yellow")
            zone_ids[domain_name] = domain_zone_id
        else:
            subdomain_zone_id = _create_hosted_zone(
                client, domain_name, parent_zone, parent_zone_id
            )
            zone_ids[domain_name] = subdomain_zone_id

    return zone_ids


def _get_hosted_zones_paginator(client):
    return client.get_paginator("list_hosted_zones").paginate()


def _get_paginated_zones(client, parent_zone, domain_zone):
    domain_zone_id = parent_zone_id = None

    for page in _get_hosted_zones_paginator(client):
        # each page is a hosted zones response type object
        hosted_zones = {hz["Name"]: hz for hz in page["HostedZones"]}

        if parent_zone in hosted_zones and parent_zone_id is None:
            parent_zone_id = hosted_zones[parent_zone]["Id"]

        if domain_zone in hosted_zones and domain_zone_id is None:
            domain_zone_id = hosted_zones[domain_zone]["Id"]

        if all([parent_zone_id, domain_zone_id]):
            # both were found, no need to further pagination
            break

    return domain_zone_id, parent_zone_id


def _create_hosted_zone(client, domain_name, parent_zone, parent_zone_id):
    if not click.confirm(
        click.style("About to create domain: ", fg="cyan")
        + click.style(f"{domain_name}\n", fg="white", bold=True)
        + click.style("Do you want to continue?", fg="cyan"),
    ):
        exit()
    response = client.create_hosted_zone(
        Name=domain_name,
        # Timestamp is on the end because CallerReference must be unique for every call
        CallerReference=f"{domain_name}_from_code_{int(time.time())}",
    )
    ns_records = response["DelegationSet"]
    subdomain_zone_id = response["HostedZone"]["Id"]
    copy_records_from_parent_to_subdomain(client, parent_zone_id, domain_name, subdomain_zone_id)
    if not click.confirm(
        click.style(f"Updating parent {parent_zone} domain with records: ", fg="cyan")
        + click.style(f"{ns_records['NameServers']}\n", fg="white", bold=True)
        + click.style("Do you want to continue?", fg="cyan"),
    ):
        exit()
    _add_subdomain_ns_records_to_parent(client, domain_name, ns_records, parent_zone_id)

    return subdomain_zone_id


def _add_subdomain_ns_records_to_parent(client, domain_name, ns_records, parent_zone_id):
    # Add nameserver records of subdomain to parent
    nameservers = ns_records["NameServers"]
    # append . to make fully qualified domain name
    nameservers = [f"{nameserver}." for nameserver in nameservers]
    nameserver_resource_records = [{"Value": nameserver} for nameserver in nameservers]
    client.change_resource_record_sets(
        HostedZoneId=parent_zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": domain_name,
                        "Type": "NS",
                        "TTL": 300,
                        "ResourceRecords": nameserver_resource_records,
                    },
                },
            ],
        },
    )


class InvalidDomainException(Exception):
    pass


def _get_subdomains_from_base(base: list[str], subdomain: list[str]) -> list[list[str]]:
    """
    Recurse over domain to get a list of subdomains.

    These are ordered from smallest to largest, so the domains can be created in
    the correct order.
    """
    if base == subdomain:
        return []
    return _get_subdomains_from_base(base, subdomain[1:]) + [subdomain]


def get_required_subdomains(base_domain: str, subdomain: str) -> list[str]:
    """
    We only want to get subdomains up to 4 levels deep.

    Prod base domains should be 3 levels deep, so we should create up to one
    additional subdomain. Dev base domain is always "uktrade.digital" and should
    have the app and env subdomains created, so 4 levels in either case.
    """
    if base_domain not in AVAILABLE_DOMAINS:
        raise InvalidDomainException(f"{base_domain} is not a supported base domain")
    _validate_subdomain(base_domain, subdomain)
    domains_as_lists = _get_subdomains_from_base(base_domain.split("."), subdomain.split("."))

    max_domain_levels = 4
    return [
        ".".join(domain_parts)
        for domain_parts in domains_as_lists
        if len(domain_parts) <= max_domain_levels
    ]


def _validate_subdomain(base_domain, subdomain):
    errors = []
    if not subdomain.endswith("." + base_domain):
        errors.append(f"{subdomain} is not a subdomain of {base_domain}")

    errors.extend(_validate_basic_domain_syntax(subdomain))

    if errors:
        raise InvalidDomainException("\n".join(errors))


def _validate_basic_domain_syntax(domain):
    errors = []
    if ".." in domain or not re.match(r"^[0-9a-zA-Z-.]+$", domain):
        errors.append(f"Subdomain {domain} is not a valid domain")

    return errors


def validate_subdomains(subdomains: list[str]) -> None:
    bad_domains = []
    for subdomain in subdomains:
        is_valid = False
        for key in AVAILABLE_DOMAINS:
            if subdomain.endswith(key):
                is_valid = True
                break
        if not is_valid:
            bad_domains.append(subdomain)
    if bad_domains:
        csv_domains = ", ".join(bad_domains)
        raise InvalidDomainException(
            f"The following subdomains do not have one of the allowed base domains: {csv_domains}"
        )


def get_base_domain(subdomains: list[str]) -> str:
    matching_domains = set()
    domains_by_length = sorted(AVAILABLE_DOMAINS.keys(), key=lambda d: len(d), reverse=True)
    for subdomain in subdomains:
        for domain_name in domains_by_length:
            if subdomain.endswith(f".{domain_name}"):
                matching_domains.add(domain_name)
                break

    if len(matching_domains) > 1:
        ordered_subdomains = ", ".join(sorted(matching_domains))
        raise InvalidDomainException(f"Multiple base domains were found: {ordered_subdomains}")

    if not matching_domains:
        ordered_subdomains = ", ".join(sorted(subdomains))
        raise InvalidDomainException(
            f"No base domains were found for subdomains: {ordered_subdomains}"
        )

    return matching_domains.pop()


def get_certificate_zone_id(hosted_zones):
    hosted_zone_names = sorted([zone for zone in hosted_zones], key=lambda z: len(z))
    longest_hosted_zone = hosted_zone_names[-1]

    return hosted_zones[longest_hosted_zone]


def create_required_zones_and_certs(domain_client, project_client, subdomain, base_domain):
    hosted_zones = create_hosted_zones(domain_client, base_domain, subdomain)

    cert_zone_id = get_certificate_zone_id(hosted_zones)

    return create_cert(project_client, domain_client, subdomain, cert_zone_id)


@click.group(chain=True, cls=ClickDocOptGroup)
def domain():
    check_platform_helper_version_needs_update()


@domain.command()
@click.option(
    "--project-profile", help="AWS account profile name for certificates account", required=True
)
@click.option("--env", help="AWS Copilot environment name", required=True)
def configure(project_profile, env):
    """Creates subdomains if they do not exist and then creates certificates for
    them."""

    # If you need to reset to debug this command, you will need to delete any of the following
    # which have been created:
    # the certificate in your application's AWS account,
    # the hosted zone for the application environment in the dev AWS account,
    # and the applications records on the hosted zone for the environment in the dev AWS account.

    manifests = _get_manifests_or_abort()

    subdomains = _get_subdomains_from_env_manifests(env, manifests)
    validate_subdomains(subdomains)
    base_domain = get_base_domain(subdomains)
    domain_profile = AVAILABLE_DOMAINS[base_domain]

    domain_session = get_aws_session_or_abort(domain_profile)
    project_session = get_aws_session_or_abort(project_profile)
    domain_client = domain_session.client("route53")
    project_client = project_session.client("acm", region_name=AWS_CERT_REGION)

    cert_list = {}

    for subdomain in subdomains:
        cert_arn = create_required_zones_and_certs(
            domain_client,
            project_client,
            subdomain,
            base_domain,
        )
        cert_list.update({subdomain: cert_arn})

    if cert_list:
        click.secho("\nHere are your Certificate ARNs:", fg="cyan")
        for domain, cert in cert_list.items():
            click.secho(f"Domain: {domain} => Cert ARN: {cert}", fg="white", bold=True)
    else:
        click.secho("No domains found, please check the manifest file", fg="red")


def _get_domain_aliases(conf, environment):
    aliases = []
    for env, domain in conf["environments"].items():
        if env == environment:
            # ensure configure doesn't blow up when http or alias
            # are missing
            if domain.get("http") and domain.get("http").get("alias"):
                aliases.append(domain["http"]["alias"])
    return aliases


def _get_subdomains_from_env_manifests(environment, manifests):
    subdomains = []
    for manifest in manifests:
        # Need to check that the manifest file is correctly configured.
        with open(manifest, "r") as fd:
            conf = yaml.safe_load(fd)
            if "environments" in conf:
                click.echo(
                    click.style("Checking file: ", fg="cyan") + click.style(manifest, fg="white"),
                )
                aliases = _get_domain_aliases(conf, environment)
                if not len(aliases):
                    click.echo(
                        click.style(
                            f"No http.alias present for {environment} environment in {manifest}, skipping...",
                            fg="cyan",
                        ),
                    )
                else:
                    click.secho("Domains listed in manifest file", fg="cyan", underline=True)
                    click.secho(
                        "  " + "\n  ".join(aliases),
                        fg="yellow",
                        bold=True,
                    )
                    subdomains.extend(aliases)
    return subdomains


def _get_manifests_or_abort():
    if not os.path.exists(COPILOT_DIR):
        abort_with_error("Please check path, copilot directory appears to be missing.")

    manifests = []
    for root, dirs, files in os.walk(COPILOT_DIR):
        for file in files:
            if file == "manifest.yml" or file == "manifest.yaml":
                manifests.append(os.path.join(root, file))

    if not manifests:
        abort_with_error("Please check path, no manifest files were found")

    return manifests


@domain.command()
@click.option("--app", help="Application Name", required=True)
@click.option("--env", help="Environment", required=True)
@click.option("--svc", help="Service Name", required=True)
@click.option(
    "--domain-profile",
    help="AWS account profile name for Route53 domains account",
    required=True,
    type=click.Choice(["dev", "live"]),
)
@click.option(
    "--project-profile", help="AWS account profile name for application account", required=True
)
def assign(app, domain_profile, project_profile, svc, env):
    """Assigns the load balancer for a service to its domain name."""
    domain_session = get_aws_session_or_abort(domain_profile)
    project_session = get_aws_session_or_abort(project_profile)

    if not Path("./copilot").exists() or not Path("./copilot").is_dir():
        click.secho(
            "Cannot find copilot directory. Run this command in the root of the deployment repository.",
            bg="red",
        )
        exit(1)
    # Find the Load Balancer name.
    domain_name, load_balancer_configuration = get_load_balancer_domain_and_configuration(
        project_session, app, env, svc
    )
    elb_name = load_balancer_configuration["DNSName"]

    click.echo(
        click.style("The Domain: ", fg="yellow")
        + click.style(f"{domain_name}\n", fg="white", bold=True)
        + click.style("has been assigned the Load Balancer: ", fg="yellow")
        + click.style(f"{elb_name}\n", fg="white", bold=True)
        + click.style("Checking to see if this is in Route53", fg="yellow"),
    )

    domain_client = domain_session.client("route53")
    response = domain_client.list_hosted_zones_by_name()
    check_response(response)

    # Scan Route53 Zone for matching domains and update records if needed.
    hosted_zones = {}
    for hz in response["HostedZones"]:
        hosted_zones[hz["Name"]] = hz

    parts = domain_name.split(".")
    for _ in range(len(parts) - 1):
        subdomain = ".".join(parts) + "."
        click.echo(
            click.style("Searching for ", fg="yellow")
            + click.style(f"{subdomain}..", fg="white", bold=True)
        )

        if subdomain in hosted_zones:
            click.echo(
                click.style("Found hosted zone ", fg="yellow")
                + click.style(hosted_zones[subdomain]["Name"], fg="white", bold=True),
            )
            hosted_zone_id = hosted_zones[subdomain]["Id"]

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
                        + click.style(
                            f"{record['ResourceRecords'][0]['Value']}", fg="white", bold=True
                        ),
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

            record = {
                "Name": domain_name,
                "Type": "CNAME",
                "TTL": 300,
                "ResourceRecords": [{"Value": elb_name}],
            }

            if not click.confirm(
                click.style("Creating Route53 record: ", fg="yellow")
                + click.style(
                    f"{record['Name']} -> {record['ResourceRecords'][0]['Value']}\n",
                    fg="white",
                    bold=True,
                )
                + click.style("In Domain: ", fg="yellow")
                + click.style(f"{subdomain}", fg="white", bold=True)
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


def update_rule(delete, listener, conditions, rule_arn, elb_client, acm_client, cdn_domain):
    # Update Rule
    response = elb_client.modify_rule(RuleArn=rule_arn, Conditions=conditions)
    check_response(response)

    # Create certificate if not already present.
    base_domain = get_base_domain([cdn_domain])
    domain_profile = AVAILABLE_DOMAINS[base_domain]
    domain_session = get_aws_session_or_abort(domain_profile)
    r53_client = domain_session.client("route53")
    cert_arn = create_required_zones_and_certs(
        r53_client,
        acm_client,
        cdn_domain,
        base_domain,
    )

    # Attach/Remove certificate from LB.
    if delete:
        response = elb_client.remove_listener_certificates(
            ListenerArn=listener["ListenerArn"],
            Certificates=[
                {
                    "CertificateArn": cert_arn,
                },
            ],
        )
    else:
        response = elb_client.add_listener_certificates(
            ListenerArn=listener["ListenerArn"],
            Certificates=[
                {
                    "CertificateArn": cert_arn,
                },
            ],
        )
    check_response(response)

    # List newly configured domains.
    for cond in conditions:
        if cond["Field"] == "host-header":
            click.echo(
                click.style("Domains now configured: ", fg="green")
                + click.style(
                    f"{cond['HostHeaderConfig']['Values']}",
                    fg="white",
                    bold=True,
                ),
            )


def find_domain_rules(action, delete, project_profile, env, app, svc):
    project_session = get_aws_session_or_abort(project_profile)
    elb_client = project_session.client("elbv2")
    acm_client = project_session.client("acm")

    loadbalancerarn = get_load_balancer_configuration(project_session, app, env, svc)[
        "LoadBalancers"
    ][0]["LoadBalancerArn"]

    response = elb_client.describe_listeners(
        LoadBalancerArn=loadbalancerarn,
    )
    check_response(response)

    # Certificates and domains only need to be configured on the HTTPS listener.
    for listener in response["Listeners"]:
        if listener["Protocol"] == "HTTPS":
            response = elb_client.describe_rules(
                ListenerArn=listener["ListenerArn"],
            )
            # If there are multiple services there will be more than two rules
            # (1 default, 1 custom domain).
            if len(response["Rules"]) > 2:
                click.echo(
                    click.style(
                        f"Note: Multiple Domains are configured on this Load Balancer.\n",
                        fg="blue",
                        bold=True,
                    ),
                )

            # Get the current rule so we can update host header with new domain.
            for rule in response["Rules"]:
                save = True
                rule_arn = rule["RuleArn"]
                conditions = rule["Conditions"]

                if conditions:
                    for cond in conditions:
                        # Only check if the condition is using the host header
                        if cond["Field"] == "host-header":
                            values_string = ";".join(cond["Values"])
                            click.echo(
                                click.style("Domains currently configured: ", fg="yellow")
                                + click.style(f"{values_string}", fg="white", bold=True),
                            )
                            cdn_domain = input(
                                "Enter in domain you wish to remove (or press Enter to skip): "
                                if delete
                                else "Enter in domain you wish to add (or press Enter to skip): "
                            )

                            if not cdn_domain:
                                save = False
                                break

                            save = action(cond, cdn_domain)

                            if not save:
                                break

                            cond.pop("Values", None)

                        if cond["Field"] == "path-pattern":
                            cond.pop("PathPatternConfig", None)

                    if save:
                        update_rule(
                            delete,
                            listener,
                            conditions,
                            rule_arn,
                            elb_client,
                            acm_client,
                            cdn_domain,
                        )
            break


@click.group(chain=True, cls=ClickDocOptGroup)
def cdn():
    check_platform_helper_version_needs_update()


@cdn.command(name="assign")
@click.option(
    "--project-profile", help="AWS account profile name for certificates account", required=True
)
@click.option("--env", help="AWS Copilot environment name", required=True)
@click.option("--app", help="Application Name", required=True)
@click.option("--svc", help="Service Name", required=True)
def cdn_assign(project_profile, env, app, svc):
    """Assigns a CDN domain name to application loadbalancer."""

    def assign_domain(cond, cdn_domain):
        if cdn_domain in cond["Values"]:
            click.echo(
                click.style(f"{cdn_domain} already exists, exiting", fg="red"),
            )
            save = False
            return save

        cond["HostHeaderConfig"]["Values"].append(cdn_domain)
        save = True
        return save

    find_domain_rules(assign_domain, False, project_profile, env, app, svc)


@cdn.command(name="delete")
@click.option(
    "--project-profile", help="AWS account profile name for certificates account", required=True
)
@click.option("--env", help="AWS Copilot environment name", required=True)
@click.option("--app", help="Application Name", required=True)
@click.option("--svc", help="Service Name", required=True)
# Feature to be added at later date if needed, there shouldn't be a need to remove all domains
# @click.option("--force", help="Force remove", is_flag=True)
def cdn_delete(project_profile, env, app, svc, force=False):
    """Assigns a CDN domain name to application loadbalancer."""

    def delete_domain(cond, cdn_domain):
        if click.confirm(
            click.style("Are you sure you wish to delete the domain ", fg="yellow")
            + click.style(f"{cdn_domain}?", fg="white", bold=True),
        ):
            # Exit if specified domain doesn't exist.
            if cdn_domain not in cond["Values"]:
                click.echo(
                    click.style(f"{cdn_domain} doesn't exists, exiting", fg="red"),
                )
                save = False
                return save

            # At present at least 1 domain needs to be on the listener.
            if len(cond["Values"]) == 1 and not force:
                click.echo(
                    click.style(
                        f"{cdn_domain} is the only domain configured on the "
                        + "LoadBalancer, exiting",
                        fg="red",
                    ),
                )
                save = False
                return save

            click.echo(
                click.style(f"deleting {cdn_domain}", fg="green"),
            )
            cond["HostHeaderConfig"]["Values"].remove(cdn_domain)
            save = True
            return save
        # Exit if not sure.
        else:
            save = False
            return save

    find_domain_rules(delete_domain, True, project_profile, env, app, svc)


@cdn.command(name="list")
@click.option(
    "--project-profile", help="AWS account profile name for certificates account", required=True
)
@click.option("--env", help="AWS Copilot environment name", required=True)
@click.option("--app", help="Application Name", required=True)
@click.option("--svc", help="Service Name", required=True)
def cdn_list(project_profile, env, app, svc):
    """List CDN domain name attached to application loadbalancer."""
    project_session = get_aws_session_or_abort(project_profile)

    elb_client = project_session.client("elbv2")

    loadbalancerarn = get_load_balancer_configuration(project_session, app, env, svc)[
        "LoadBalancers"
    ][0]["LoadBalancerArn"]

    response = elb_client.describe_listeners(
        LoadBalancerArn=loadbalancerarn,
    )
    check_response(response)

    for listener in response["Listeners"]:
        if listener["Protocol"] == "HTTPS":
            response = elb_client.describe_rules(
                ListenerArn=listener["ListenerArn"],
            )

            # Get the current rule so we can list the configured domains.
            for rule in response["Rules"]:
                conditions = rule["Conditions"]
                if conditions:
                    for cond in conditions:
                        if cond["Field"] == "host-header":
                            click.echo(
                                click.style("Domains currently configured: ", fg="yellow")
                                + click.style(f"{cond['Values']}", fg="white", bold=True),
                            )


if __name__ == "__main__":
    domain()
