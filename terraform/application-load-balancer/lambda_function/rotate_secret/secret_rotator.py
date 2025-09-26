import json
import os
import time
from typing import Any
from typing import Dict
from typing import List
from typing import Tuple

import boto3
import requests
from botocore.exceptions import ClientError
from slack_service import SlackNotificationService

AWSPENDING = "AWSPENDING"
AWSCURRENT = "AWSCURRENT"


class SecretRotator:
    def __init__(self, logger, **kwargs):
        self.logger = logger
        # Use provided values or default to provided Lambda environment variables
        self.secret_id = kwargs.get("secret_id", os.environ.get("SECRETID"))
        self.waf_acl_name = kwargs.get("waf_acl_name", os.environ.get("WAFACLNAME"))
        self.waf_acl_id = kwargs.get("waf_acl_id", os.environ.get("WAFACLID"))
        waf_rule_priority = kwargs.get("waf_rule_priority", os.environ.get("WAFRULEPRI"))
        try:
            self.waf_rule_priority = int(waf_rule_priority)
        except (TypeError, ValueError):
            self.waf_rule_priority = 0
        self.header_name = kwargs.get("header_name", os.environ.get("HEADERNAME"))
        self.application = kwargs.get("application", os.environ.get("APPLICATION"))
        self.environment = kwargs.get("environment", os.environ.get("ENVIRONMENT"))
        self.role_arn = kwargs.get("role_arn", os.environ.get("ROLEARN"))
        self.distro_list = kwargs.get("distro_list", os.environ.get("DISTROIDLIST"))
        self.aws_account = kwargs.get("aws_account", os.environ.get("AWS_ACCOUNT"))

        slack_token = kwargs.get("slack_token", os.environ.get("SLACK_TOKEN"))
        slack_channel = kwargs.get("slack_channel", os.environ.get("SLACK_CHANNEL"))
        self.slack_service = None
        if slack_token and slack_channel:
            self.slack_service = SlackNotificationService(
                slack_token, slack_channel, self.aws_account
            )
        self.waf_sleep_duration = int(
            kwargs.get("waf_sleep_duration", os.environ.get("WAF_SLEEP_DURATION", 75))
        )

    def get_cloudfront_client(self) -> boto3.client:
        sts = boto3.client("sts")
        credentials = sts.assume_role(RoleArn=self.role_arn, RoleSessionName="rotation_session")[
            "Credentials"
        ]
        return boto3.client(
            "cloudfront",
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )

    def get_deployed_distributions(self) -> List[Dict[str, Any]]:
        client = self.get_cloudfront_client()
        paginator = client.get_paginator("list_distributions")
        matching_distributions = []

        for page in paginator.paginate():
            for distribution in page.get("DistributionList", {}).get("Items", []):
                aliases = distribution.get("Aliases", {}).get("Items", [])
                if any(domain in aliases for domain in self.distro_list.split(",")):
                    matching_distributions.append(
                        {
                            "Id": distribution["Id"],
                            "Origin": distribution["Origins"]["Items"][0]["DomainName"],
                            "Domain": distribution["Aliases"]["Items"][0],
                        }
                    )
        self.logger.info(f"Matched cloudfront distributions: {matching_distributions}")
        return matching_distributions

    def get_waf_acl(self) -> Dict[str, Any]:
        client = boto3.client("wafv2")
        return client.get_web_acl(Name=self.waf_acl_name, Scope="REGIONAL", Id=self.waf_acl_id)

    def _create_byte_match_statement(self, search_string: str) -> Dict[str, Any]:
        return {
            "ByteMatchStatement": {
                "FieldToMatch": {"SingleHeader": {"Name": self.header_name}},
                "PositionalConstraint": "EXACTLY",
                "SearchString": search_string,
                "TextTransformations": [{"Type": "NONE", "Priority": 0}],
            }
        }

    def update_waf_acl(self, new_secret: str, prev_secret: str) -> None:
        client = boto3.client("wafv2")
        waf_acl = self.get_waf_acl()
        lock_token = waf_acl["LockToken"]
        metric_name = f"{self.application}-{self.environment}-XOriginVerify"
        rule = {
            "Name": f"{self.application}{self.environment}XOriginVerify",
            "Priority": self.waf_rule_priority,
            "Action": {"Allow": {}},
            "VisibilityConfig": {
                "SampledRequestsEnabled": True,
                "CloudWatchMetricsEnabled": True,
                "MetricName": metric_name,
            },
            "Statement": {
                "OrStatement": {
                    "Statements": [
                        self._create_byte_match_statement(new_secret),
                        self._create_byte_match_statement(prev_secret),
                    ]
                }
            },
        }

        new_rules = [rule] + [
            r for r in waf_acl["WebACL"]["Rules"] if r["Priority"] != self.waf_rule_priority
        ]
        self.logger.info("Updating WAF WebACL with new rules.")

        response = client.update_web_acl(
            Name=self.waf_acl_name,
            Scope="REGIONAL",
            Id=self.waf_acl_id,
            LockToken=lock_token,
            DefaultAction={"Block": {}},
            Description="CloudFront Origin Verify",
            VisibilityConfig={
                "SampledRequestsEnabled": True,
                "CloudWatchMetricsEnabled": True,
                "MetricName": metric_name,
            },
            Rules=new_rules,
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            self.logger.info("WAF WebACL rules updated")

    def get_cf_distro(self, distro_id: str) -> Dict:
        """Fetches the CloudFront distribution details."""
        client = self.get_cloudfront_client()
        return client.get_distribution(Id=distro_id)

    def get_cf_distro_config(self, distro_id: str) -> Dict:
        """Fetches the configuration of a CloudFront distribution."""
        client = self.get_cloudfront_client()
        return client.get_distribution_config(Id=distro_id)

    def update_cf_distro(self, distro_id: str, header_value: str) -> Dict:
        """
        Updates the custom headers for a CloudFront distribution.

        Args:
            distro_id (str): The ID of the CloudFront distribution.
            header_value (str): The header value to set for the custom header.
        """
        client = self.get_cloudfront_client()

        if not self.is_distribution_deployed(distro_id):
            self.logger.error(f"Distribution Id: {distro_id} status is not Deployed.")
            raise ValueError(f"Distribution Id: {distro_id} status is not Deployed.")

        dist_config = self.get_cf_distro_config(distro_id)

        self.update_custom_headers(dist_config, header_value)

        # Update the distribution
        try:
            return self.apply_distribution_update(client, distro_id, dist_config)

        except RuntimeError as e:
            self.logger.error(
                f"Failed to update custom headers for distribution Id {distro_id}: {e}"
            )
            raise

    def is_distribution_deployed(self, distro_id: str) -> bool:
        """Checks if the CloudFront distribution is deployed."""
        dist_status = self.get_cf_distro(distro_id)
        return "Deployed" in dist_status["Distribution"]["Status"]

    def update_custom_headers(self, dist_config: Dict, header_value: str) -> bool:
        """
        Updates or creates given custom header in the distribution config.

        Returns True if any headers were updated or created.
        """
        header_count = 0

        for origin in dist_config["DistributionConfig"]["Origins"]["Items"]:
            if "CustomHeaders" not in origin or origin["CustomHeaders"]["Quantity"] == 0:
                self.logger.info(
                    f"No custom headers exist. Creating new custom header for origin: {origin['Id']}"
                )
                origin["CustomHeaders"] = {
                    "Quantity": 1,
                    "Items": [{"HeaderName": self.header_name, "HeaderValue": header_value}],
                }
                header_count += 1
                continue

            found_header = False
            for header in origin["CustomHeaders"]["Items"]:
                if header["HeaderName"] == self.header_name:
                    self.logger.info(f"Updating existing custom header for origin: {origin['Id']}")
                    header["HeaderValue"] = header_value
                    found_header = True
                    header_count += 1
                    break

            if not found_header:
                self.logger.info(
                    f"Adding new custom header to existing headers for origin: {origin['Id']}"
                )
                origin["CustomHeaders"]["Items"].append(
                    {"HeaderName": self.header_name, "HeaderValue": header_value}
                )
                origin["CustomHeaders"]["Quantity"] += 1
                header_count += 1

        return header_count > 0

    def apply_distribution_update(self, client, distro_id: str, dist_config: Dict) -> Dict:
        """Applies the distribution update to CloudFront."""
        try:
            response = client.update_distribution(
                Id=distro_id,
                IfMatch=dist_config["ResponseMetadata"]["HTTPHeaders"]["etag"],
                DistributionConfig=dist_config["DistributionConfig"],
            )

            status_code = response["ResponseMetadata"]["HTTPStatusCode"]

            if status_code == 200:
                self.logger.info(f"CloudFront distribution {distro_id} updated successfully")
            else:
                self.logger.warning(
                    f"Failed to update CloudFront distribution {distro_id}. Status code: {status_code}"
                )
                raise RuntimeError(
                    f"Failed to update CloudFront distribution {distro_id}. Status code: {status_code}"
                )

            return response

        except Exception as e:
            self.logger.error(f"Error updating CloudFront distribution {distro_id}: {str(e)}")
            raise

    def process_cf_distributions_and_WAF_rules(
        self, matching_distributions, pending_secret, current_secret
    ):
        """
        Process CloudFront distributions based on whether the custom header is
        already present.

        If the custom header is missing, it will be added to the distribution.
        Updates the WAF ACL & the CloudFront distributions with the AWSPENDING &
        AWSCURRENT secret values. This method should set the AWSPENDING secret
        in the service that the secret belongs to. Sleep default 75 seconds to
        allow resources to update
        """
        all_have_header = True  # Assume all distributions have the header initially

        for distro in matching_distributions:
            distro_id = distro["Id"]
            dist_config = self.get_cf_distro_config(distro_id)

            # Track if the header was found or added in this distribution
            header_found = False

            for origin in dist_config["DistributionConfig"]["Origins"]["Items"]:
                # Check if 'Items' exists inside 'CustomHeaders', if not, initialise it
                if "Items" not in origin["CustomHeaders"]:
                    self.logger.info(
                        f"CustomHeaders empty for origin {origin['Id']}, adding custom header."
                    )
                    origin["CustomHeaders"]["Items"] = [
                        {
                            "HeaderName": self.header_name,
                            "HeaderValue": pending_secret["HEADERVALUE"],
                        }
                    ]
                    self.logger.info(
                        f"Custom header added in CloudFront distribution: {origin['Id']}"
                    )
                    # Mark that we modified this distribution by adding the header
                    all_have_header = False
                else:
                    # If 'Items' exists, check if the custom header is present
                    header_found = any(
                        header["HeaderName"] == self.header_name
                        for header in origin["CustomHeaders"]["Items"]
                    )

                    # If the header is not found, add it
                    if not header_found:
                        self.logger.info(
                            f"Custom header not found in origin {origin}, adding header."
                        )
                        origin["CustomHeaders"]["Items"].append(
                            {
                                "HeaderName": self.header_name,
                                "HeaderValue": pending_secret["HEADERVALUE"],
                            }
                        )

                        self.logger.info(
                            f"Custom header found/added in CloudFront distribution: {origin}"
                        )
                        all_have_header = False  # Mark this as needing update, since we added it

                # If header is found in the Items, we can break out of the loop for this origin
                if header_found:
                    break

            # If header was not found and added in any of the origins, we mark all_have_header as False
            if not header_found:
                all_have_header = False

        if all_have_header:
            # If all CF distributions have the header, update WAF rule first
            self.logger.info(
                "Updating WAF rule first. All CloudFront distributions already have custom header."
            )
            self.update_waf_acl(pending_secret["HEADERVALUE"], current_secret["HEADERVALUE"])

            # Sleep for default 75 seconds for regional WAF config propagation
            self.logger.info(
                f"Sleeping for {self.waf_sleep_duration} seconds for WAF rule propagation."
            )
            time.sleep(self.waf_sleep_duration)

        # Update each CloudFront distribution
        for distro in matching_distributions:
            try:
                self.logger.info(f"Updating CloudFront distribution {distro['Id']}.")
                self.update_cf_distro(distro["Id"], pending_secret["HEADERVALUE"])
            except Exception as e:
                self.logger.error(f"Failed to update distribution {distro['Id']}: {e}")
                raise

        if not all_have_header:
            # If not all CF distributions had the header, update WAF last
            self.logger.info("Not all CloudFront distributions have the header. Updating WAF last.")
            self.update_waf_acl(pending_secret["HEADERVALUE"], current_secret["HEADERVALUE"])

            # Sleep for default 75 seconds for regional WAF config propagation
            self.logger.info(
                f"Sleeping for {self.waf_sleep_duration} seconds for WAF rule propagation."
            )
            time.sleep(self.waf_sleep_duration)

    def run_test_origin_access(self, url: str, secret: str) -> bool:
        try:
            response = requests.get(
                url,
                headers={self.header_name: secret},
                timeout=(5, 10),  # 3-second connection timeout, 5-second read timeout
            )
            self.logger.info(f"Testing URL, {url} - response code, {response.status_code}")

            # Log additional response details for debugging
            if response.status_code != 200:
                self.logger.error(f"Non-200 response for URL {url}")
                self.logger.error(f"Response Status Code: {response.status_code}")
                self.logger.error(f"Response Headers: {response.headers}")
                try:
                    self.logger.error(
                        f"Response Content: {response.text[:500]}"
                    )  # Limit content to first 500 chars
                except Exception as content_error:
                    self.logger.error(f"Could not log response content: {str(content_error)}")

            return response.status_code == 200

        except requests.exceptions.ConnectionError as conn_err:
            self.logger.error(f"Connection error for URL {url}")
            self.logger.error(f"Connection Error Details: {str(conn_err)}")
            # Log more specific connection error details
            if hasattr(conn_err, "response"):
                self.logger.error(f"Connection Error Response: {conn_err.response}")
            return False

        except requests.exceptions.Timeout as timeout_err:
            self.logger.error(f"Timeout error for URL {url}")
            self.logger.error(f"Timeout Error Details: {str(timeout_err)}")
            return False

        except requests.exceptions.TooManyRedirects as redirect_err:
            self.logger.error(f"Too many redirects for URL {url}")
            self.logger.error(f"Redirect Error Details: {str(redirect_err)}")
            return False

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Unhandled request error for URL {url}")
            self.logger.error(f"Error Type: {type(e).__name__}")
            self.logger.error(f"Error Details: {str(e)}")

            # Additional context if available
            if hasattr(e, "response"):
                try:
                    self.logger.error(f"Error Response Status Code: {e.response.status_code}")
                    self.logger.error(f"Error Response Headers: {e.response.headers}")
                    self.logger.error(
                        f"Error Response Content: {e.response.text[:500]}"
                    )  # Limit content to first 500 chars
                except Exception as log_err:
                    self.logger.error(f"Could not log error response details: {str(log_err)}")

            return False

        except Exception as unexpected_err:
            self.logger.error(f"Unexpected error testing URL {url}")
            self.logger.error(f"Unexpected Error Type: {type(unexpected_err).__name__}")
            self.logger.error(f"Unexpected Error Details: {str(unexpected_err)}")
            return False

    def get_secrets(self, service_client, arn: str) -> Tuple[Dict, Dict]:
        metadata = service_client.describe_secret(SecretId=arn)
        version_stages = metadata.get("VersionIdsToStages", {})
        current_version = None
        pending_version = None

        for version, stages in version_stages.items():
            if AWSCURRENT in stages:
                current_version = version
                self.logger.info(f"Found AWSCURRENT version: {version}")
            if AWSPENDING in stages:
                pending_version = version
                self.logger.info(f"Found AWSPENDING version: {version}")

        if not current_version:
            raise ValueError("No AWSCURRENT version found")

        if not pending_version:
            raise ValueError("No AWSPENDING version found")

        try:
            current = service_client.get_secret_value(
                SecretId=arn, VersionId=current_version, VersionStage=AWSCURRENT
            )

            pending = service_client.get_secret_value(
                SecretId=arn, VersionId=pending_version, VersionStage=AWSPENDING
            )
        except service_client.exceptions.ResourceNotFoundException as e:
            self.logger.error(f"Failed to retrieve secret values: {e}")
            raise

        pending_secret = json.loads(pending["SecretString"])
        current_secret = json.loads(current["SecretString"])

        return pending_secret, current_secret

    def create_secret(self, service_client, arn, token):
        # Make sure the current secret exists
        try:
            service_client.get_secret_value(SecretId=arn, VersionStage="AWSCURRENT")
            self.logger.info("Successfully retrieved AWSCURRENT version for secret")

        except service_client.exceptions.ResourceNotFoundException:
            self.logger.error("AWSCURRENT version does not exist for secret")

        try:
            service_client.get_secret_value(
                SecretId=arn, VersionId=token, VersionStage="AWSPENDING"
            )
            self.logger.info("Successfully retrieved AWSPENDING version for secret")
        except service_client.exceptions.ResourceNotFoundException:
            # Generate a random password for AWSPENDING
            passwd = service_client.get_random_password(ExcludePunctuation=True)
            self.logger.info("Generate new password for AWSPENDING for secret")

            try:
                service_client.put_secret_value(
                    SecretId=arn,
                    ClientRequestToken=token,
                    SecretString=json.dumps({"HEADERVALUE": passwd["RandomPassword"]}),
                    VersionStages=["AWSPENDING"],
                )
                self.logger.info(
                    "Successfully created AWSPENDING version stage and secret value for secret"
                )
            except Exception as e:
                self.logger.error(f"Failed to create AWSPENDING version for secret. Error: {e}")
                raise

    def set_secret(self, service_client, arn, token):
        """
        Set the secret Updates the WAF ACL & the CloudFront distributions with
        the AWSPENDING & AWSCURRENT secret values.

        This method should set the AWSPENDING secret in the service that the secret belongs to.
        Sleep default 75 seconds to allow resources to update
        Args:
            service_client (client): The secrets manager service client
            arn (string): The secret ARN or other identifier
            token (string): The ClientRequestToken associated with the secret version
        """
        # Confirm CloudFront distributions are in Deployed state
        matching_distributions = self.get_deployed_distributions()

        if not matching_distributions:
            self.logger.error(
                "No matching distributions found. Cannot update Cloudfront distributions or WAF ACLs"
            )
            raise ValueError(
                "No matching distributions found. Cannot update Cloudfront distributions or WAF ACLs"
            )

        for distro in matching_distributions:
            self.logger.info(f"Getting status of distro: {distro['Id']}")

            if not self.is_distribution_deployed(distro["Id"]):
                self.logger.error(f"Distribution Id, {distro['Id']} status is not Deployed.")
                raise ValueError(f"Distribution Id, {distro['Id']} status is not Deployed.")
            else:
                self.logger.info(f"Distro {distro['Id']} is deployed")

        # Obtain secret value for AWSPENDING
        pending = service_client.get_secret_value(
            SecretId=arn, VersionId=token, VersionStage="AWSPENDING"
        )

        # Obtain secret value for AWSCURRENT
        metadata = service_client.describe_secret(SecretId=arn)
        for version in metadata["VersionIdsToStages"]:
            self.logger.info("Getting AWSCURRENT version")
            if "AWSCURRENT" in metadata["VersionIdsToStages"][version]:
                currenttoken = version
                current = service_client.get_secret_value(
                    SecretId=arn, VersionId=currenttoken, VersionStage="AWSCURRENT"
                )

        pendingsecret = json.loads(pending["SecretString"])
        currentsecret = json.loads(current["SecretString"])

        # Update regional WAF WebACL rule and CloudFront custom header with AWSPENDING and AWSCURRENT
        try:
            self.process_cf_distributions_and_WAF_rules(
                matching_distributions, pendingsecret, currentsecret
            )

        except ClientError as e:
            self.logger.error(f"Error updating resources: {e}")
            raise ValueError(
                f"Failed to update resources CloudFront Distro Id {distro['Id']} , WAF WebACL Id {self.waf_acl_id}"
            ) from e

    def run_test_secret(self, service_client, arn, token, test_domains=[]):
        """
        Test the secret This method validates that the AWSPENDING secret works
        in the service.

        If any tests fail:
        1. Attempts to send a Slack notification (notification failure won't stop the rotation process)
        2. If Lambda event contains key TestDomains and provided domains to test, then you can trigger a Slack notification to the configured Slack channel
        """
        test_failures = []

        # Check for TestDomains key in the Lambda event - currently only used in console to test Slack message is emitted
        if test_domains:
            self.logger.info(
                "TestDomains key exists in Lambda event - testing provided dummy domains only"
            )
            for test_domain in test_domains:
                self.logger.info(f"Testing dummy distro: {test_domain}")
                error_msg = f"Simulating test failure for domain: http://{test_domain}"
                self.logger.error(error_msg)
                test_failures.append(
                    {
                        "domain": test_domain,
                        "error": error_msg,
                    }
                )

        else:
            # Obtain secret value for AWSPENDING
            pending = service_client.get_secret_value(
                SecretId=arn, VersionId=token, VersionStage="AWSPENDING"
            )

            # Obtain secret value for AWSCURRENT
            metadata = service_client.describe_secret(SecretId=arn)
            for version in metadata["VersionIdsToStages"]:
                if "AWSCURRENT" in metadata["VersionIdsToStages"][version]:
                    currenttoken = version
                    current = service_client.get_secret_value(
                        SecretId=arn, VersionId=currenttoken, VersionStage="AWSCURRENT"
                    )
                    self.logger.info("Getting AWSCURRENT version")

            pendingsecret = json.loads(pending["SecretString"])
            currentsecret = json.loads(current["SecretString"])

            secrets = [pendingsecret["HEADERVALUE"], currentsecret["HEADERVALUE"]]

            distro_list = self.get_deployed_distributions()
            for distro in distro_list:
                self.logger.info(f"Testing distro: {distro['Id']}")
                try:
                    for s in secrets:
                        if self.run_test_origin_access("http://" + distro["Domain"], s):
                            self.logger.info(f"Domain ok for http://{distro['Domain']}")
                        else:
                            error_msg = f"Tests failed for URL, http://{distro['Domain']}"
                            self.logger.error(error_msg)
                            test_failures.append(
                                {
                                    "domain": distro["Domain"],
                                    "secret_type": (
                                        "PENDING"
                                        if s == pendingsecret["HEADERVALUE"]
                                        else "CURRENT"
                                    ),
                                    "error": "Connection failed or non-200 response",
                                }
                            )
                except Exception as e:
                    error_msg = f"Error testing {distro}: {str(e)}"
                    self.logger.error(error_msg)
                    test_failures.append({"domain": distro["Domain"], "error": str(e)})

        if test_failures:
            if self.slack_service:
                try:
                    self.slack_service.send_test_failures(
                        failures=test_failures,
                        environment=self.environment,
                        application=self.application,
                    )
                except Exception as e:
                    self.logger.error(f"Failure to send Slack notification{str(e)}")

    def finish_secret(self, service_client, arn, token):
        """
        Finish the secret This method finalises the rotation process by marking
        the secret version passed in as the AWSCURRENT secret.

        Args:
            service_client (client): The secrets manager service client
            arn (string): The secret ARN or other identifier
            token (string): The ClientRequestToken associated with the secret version
        Raises:
            ResourceNotFoundException: If the secret with the specified arn does not exist
        """

        # First describe the secret to get the current version
        metadata = service_client.describe_secret(SecretId=arn)
        current_version_token = None
        for version in metadata["VersionIdsToStages"]:
            if AWSCURRENT in metadata["VersionIdsToStages"][version]:
                if version == token:
                    # The correct version is already marked as current, return
                    self.logger.info(
                        f"finishSecret: Version {version} already marked as AWSCURRENT"
                    )
                    return
                current_version_token = version
                break

        # Finalize by staging the secret version current
        service_client.update_secret_version_stage(
            SecretId=arn,
            VersionStage=AWSCURRENT,
            MoveToVersionId=token,
            RemoveFromVersionId=current_version_token,
        )
        self.logger.info(f"finishSecret: Successfully set AWSCURRENT stage to version {token}")
