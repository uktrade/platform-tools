import json
import time
from unittest.mock import MagicMock
from unittest.mock import call
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError
from secret_rotator import SecretRotator


@pytest.fixture(scope="session")
def rotator():
    """Creates a SecretRotator instance with test configuration."""
    mock_logger = MagicMock()

    return SecretRotator(
        logger=mock_logger,
        waf_acl_name="test-waf-id",
        waf_acl_id="test-waf-acl",
        waf_rule_priority="0",
        header_name="x-origin-verify",
        application="test-app",
        environment="test",
        role_arn="arn:aws:iam::123456789012:role/test-role",
        distro_list="example.com,example2.com",
        waf_sleep_duration=75,
    )


class TestCloudFrontSessionManagement:
    """Tests for CloudFront session management and credentials handling."""

    def test_assumes_correct_role_for_cloudfront_access(self, rotator):
        """The system must use STS to assume the correct role before accessing
        CloudFront."""
        # Given STS credentials for CloudFront access
        mock_credentials = {
            "Credentials": {
                "AccessKeyId": "test-access-key",
                "SecretAccessKey": "test-secret-key",
                "SessionToken": "test-session-token",
            }
        }

        mock_sts = MagicMock()
        mock_cloudfront = MagicMock()

        mock_sts.assume_role.return_value = mock_credentials

        with patch("boto3.client") as mock_boto3_client:
            mock_boto3_client.side_effect = lambda service, **kwargs: (
                mock_sts if service == "sts" else mock_cloudfront
            )

            rotator.get_cloudfront_client()

            mock_sts.assume_role.assert_called_once_with(
                RoleArn="arn:aws:iam::123456789012:role/test-role",
                RoleSessionName="rotation_session",
            )

            mock_boto3_client.assert_has_calls(
                [
                    call("sts"),
                    call(
                        "cloudfront",
                        aws_access_key_id="test-access-key",
                        aws_secret_access_key="test-secret-key",
                        aws_session_token="test-session-token",
                    ),
                ]
            )


class TestDistributionDiscovery:
    """Tests for CloudFront distribution discovery and filtering."""

    def test_identifies_distributions_that_need_secret_updates(self, rotator):
        """The lambda must identify all CloudFront distributions that need
        secret updates based on their domain aliases."""
        # Given a mix of relevant and irrelevant distributions
        mock_distributions = {
            "DistributionList": {
                "Items": [
                    {
                        "Id": "DIST1",
                        "Origins": {"Items": [{"DomainName": "origin1.example.com"}]},
                        "Aliases": {"Items": ["example.com"]},  # Should match
                    },
                    {
                        "Id": "DIST2",
                        "Origins": {"Items": [{"DomainName": "origin2.example.com"}]},
                        "Aliases": {"Items": ["example2.com"]},  # Should match
                    },
                    {
                        "Id": "DIST3",
                        "Origins": {"Items": [{"DomainName": "origin3.example.com"}]},
                        "Aliases": {"Items": ["unrelated.com"]},  # Should not match
                    },
                ]
            }
        }

        expected_result = [
            {"Id": "DIST1", "Origin": "origin1.example.com", "Domain": "example.com"},
            {"Id": "DIST2", "Origin": "origin2.example.com", "Domain": "example2.com"},
        ]

        rotator.get_cloudfront_client = MagicMock()
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [mock_distributions]

        rotator.get_cloudfront_client.return_value = mock_client

        result = rotator.get_deployed_distributions()

        assert result == expected_result, f"Expected: {expected_result}, but got: {result}"

        mock_client.get_paginator.assert_called_once_with("list_distributions")


class TestWAFManagement:
    """
    Tests for WAF rule management during secret rotation.

    These tests verify that WAF rules are updated correctly to ensure zero-
    downtime rotation.
    """

    def test_waf_contains_both_secrets_during_rotation(self, rotator):
        """During rotation, the WAF rule must accept both old and new
        secrets."""
        current_rules = {
            "WebACL": {
                "Rules": [
                    {"Priority": 1, "Name": "ExistingRule1"},
                    {"Priority": 2, "Name": "ExistingRule2"},
                ]
            },
            "LockToken": "test-lock-token",
        }

        with patch("boto3.client") as mock_boto_client:
            mock_client = MagicMock()
            mock_boto_client.return_value = mock_client

            rotator.get_waf_acl = MagicMock()
            rotator.get_waf_acl.return_value = current_rules

            # When updating the WAF ACL with both secrets
            rotator.update_waf_acl("new-secret", "old-secret")

            # Then the update should preserve existing rules
            call_args = mock_client.update_web_acl.call_args[1]
            existing_rules = [
                r for r in call_args["Rules"] if r.get("Name") in ["ExistingRule1", "ExistingRule2"]
            ]
            assert len(existing_rules) == 2, "Must preserve existing WAF rules"

            # And include both secrets in an OR condition
            secret_rule = next(
                r for r in call_args["Rules"] if r.get("Name") == "test-apptest" + "XOriginVerify"
            )
            statements = secret_rule["Statement"]["OrStatement"]["Statements"]
            header_values = [s["ByteMatchStatement"]["SearchString"] for s in statements]
            assert "new-secret" in header_values, "New secret must be in WAF rule"
            assert "old-secret" in header_values, "Old secret must be in WAF rule"

    def test_waf_update_is_atomic_with_lock_token(self, rotator):
        """WAF updates must be atomic using a lock token to prevent concurrent
        modifications."""
        # Given a WAF with a lock token
        current_rules = {"WebACL": {"Rules": []}, "LockToken": "original-lock-token"}

        with patch("boto3.client") as mock_boto_client:
            mock_client = MagicMock()
            mock_boto_client.return_value = mock_client

            rotator.get_waf_acl = MagicMock()
            rotator.get_waf_acl.return_value = current_rules

            # When updating the WAF
            rotator.update_waf_acl("new-secret", "old-secret")

            # Then it should use the lock token
            call_args = mock_client.update_web_acl.call_args[1]
            assert (
                call_args["LockToken"] == "original-lock-token"
            ), "Must use lock token for atomic updates"


class TestDistributionUpdates:
    """Tests for CloudFront distribution updates during secret rotation."""

    def test_only_updates_deployed_distributions(self, rotator):
        """Distribution updates must only proceed when the distribution is in
        'Deployed' state."""
        rotator.get_cloudfront_client = MagicMock()
        mock_client = MagicMock()

        mock_client.get_distribution.return_value = {"Distribution": {"Status": "InProgress"}}

        rotator.get_cloudfront_client.return_value = mock_client

        with pytest.raises(ValueError) as exc_info:
            rotator.update_cf_distro("DIST1", "new-header-value")

        assert "status is not Deployed" in str(exc_info.value)
        mock_client.update_distribution.assert_not_called()

    def test_updates_all_matching_custom_headers(self, rotator):
        """All custom headers matching our header name must be updated with the
        new secret."""
        # get_cf_distro - used to determine the status of the distribution
        mock_dist_status = {"Distribution": {"Status": "Deployed"}}
        # get_cf_distro_config - returns a distribution with multiple origins and headers
        mock_dist_config = {
            "DistributionConfig": {
                "Origins": {
                    "Items": [
                        {
                            "Id": "origin1",
                            "CustomHeaders": {
                                "Quantity": 2,
                                "Items": [
                                    {"HeaderName": "x-origin-verify", "HeaderValue": "old-value"},
                                    {"HeaderName": "other-header", "HeaderValue": "unchanged"},
                                ],
                            },
                        },
                        {
                            "Id": "origin2",
                            "CustomHeaders": {
                                "Quantity": 1,
                                "Items": [
                                    {"HeaderName": "x-origin-verify", "HeaderValue": "old-value"}
                                ],
                            },
                        },
                    ]
                }
            },
            "ResponseMetadata": {"HTTPHeaders": {"etag": "test-etag"}},
        }

        rotator.get_cloudfront_client = MagicMock()
        mock_client = MagicMock()
        rotator.get_cloudfront_client.return_value = mock_client

        rotator.get_cf_distro = MagicMock()
        rotator.get_cf_distro.return_value = mock_dist_status

        rotator.get_cf_distro_config = MagicMock()
        rotator.get_cf_distro_config.return_value = mock_dist_config

        mock_client.update_distribution.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

        rotator.update_cf_distro("DIST1", "new-value")

        # Then it should update all matching headers
        update_call = mock_client.update_distribution.call_args[1]
        updated_config = update_call["DistributionConfig"]

        # Verify all x-origin-verify headers were updated
        for origin in updated_config["Origins"]["Items"]:
            for header in origin["CustomHeaders"]["Items"]:
                if header["HeaderName"] == "x-origin-verify":
                    assert (
                        header["HeaderValue"] == "new-value"
                    ), f"Header not updated for origin {origin['Id']}"
                else:
                    assert (
                        header["HeaderValue"] == "unchanged"
                    ), "Non-matching headers should not be modified"

    def test_runtime_error_for_failed_distribution_update(self, rotator):
        """Test that a RuntimeError is raised when the CloudFront distribution
        update fails (i.e., when the status code is not 200)."""
        # get_cf_distro - used to determine the status of the distribution
        mock_dist_status = {"Distribution": {"Status": "Deployed"}}
        mock_dist_config = {
            "DistributionConfig": {
                "Origins": {
                    "Items": [
                        {
                            "Id": "origin1",
                            "CustomHeaders": {
                                "Quantity": 2,
                                "Items": [
                                    {"HeaderName": "x-origin-verify", "HeaderValue": "old-value"},
                                    {"HeaderName": "other-header", "HeaderValue": "unchanged"},
                                ],
                            },
                        }
                    ]
                }
            },
            "ResponseMetadata": {"HTTPHeaders": {"etag": "test-etag"}},
        }

        rotator.get_cloudfront_client = MagicMock()
        mock_client = MagicMock()
        rotator.get_cloudfront_client.return_value = mock_client

        rotator.get_cf_distro = MagicMock()
        rotator.get_cf_distro.return_value = mock_dist_status

        rotator.get_cf_distro_config = MagicMock()
        rotator.get_cf_distro_config.return_value = mock_dist_config

        mock_client.update_distribution.return_value = {"ResponseMetadata": {"HTTPStatusCode": 500}}

        with pytest.raises(RuntimeError) as excinfo:
            rotator.update_cf_distro("DIST1", "new-value")

        assert "Failed to update CloudFront distribution" in str(excinfo.value)
        assert "Status code: 500" in str(excinfo.value)

    def test_value_error_for_non_deployed_distribution(self, rotator):
        """Test that a ValueError is raised when the distribution is not
        deployed (i.e., when the `is_distribution_deployed` method returns
        False)."""
        rotator.get_cloudfront_client = MagicMock()
        mock_client = MagicMock()
        rotator.get_cloudfront_client.return_value = mock_client

        rotator.is_distribution_deployed = MagicMock()
        rotator.is_distribution_deployed.return_value = False

        # Test that the ValueError is raised when update_cf_distro is called
        with pytest.raises(ValueError) as excinfo:
            rotator.update_cf_distro("DIST1", "new-value")

        # checl exception type is correct
        if not isinstance(excinfo.value, ValueError):
            pytest.fail(f"Expected ValueError, but got {type(excinfo.value).__name__} instead.")

        assert "Distribution Id: DIST1 status is not Deployed." in str(excinfo.value)


class TestProcessCloudFrontDistributions:

    def test_all_distributions_already_have_header(self, rotator):
        """
        Test scenario where all distributions already have the custom header.

        Verify WAF update happens first, and distributions are still updated.
        """
        mock_logger = MagicMock()
        rotator.logger = mock_logger

        matching_distributions = [{"Id": "dist1"}, {"Id": "dist2"}]
        pending_secret = {"HEADERVALUE": "new-secret"}
        current_secret = {"HEADERVALUE": "old-secret"}

        def mock_get_cf_distro_config(distro_id):
            return {
                "DistributionConfig": {
                    "Origins": {
                        "Items": [
                            {
                                "Id": "origin1",
                                "CustomHeaders": {
                                    "Items": [
                                        {
                                            "HeaderName": "x-origin-verify",
                                            "HeaderValue": "existing-secret",
                                        }
                                    ]
                                },
                            }
                        ]
                    }
                }
            }

        rotator.get_cf_distro_config = mock_get_cf_distro_config

        rotator.update_waf_acl = MagicMock()
        rotator.update_cf_distro = MagicMock()
        time.sleep = MagicMock()

        rotator.process_cf_distributions_and_WAF_rules(
            matching_distributions, pending_secret, current_secret
        )

        rotator.update_waf_acl.assert_called_once_with(
            pending_secret["HEADERVALUE"], current_secret["HEADERVALUE"]
        )

        time.sleep.assert_called_once_with(rotator.waf_sleep_duration)

        rotator.update_cf_distro.assert_has_calls(
            [
                call("dist1", pending_secret["HEADERVALUE"]),
                call("dist2", pending_secret["HEADERVALUE"]),
            ],
            any_order=False,
        )

        mock_logger.info.assert_any_call(
            "Updating WAF rule first. All CloudFront distributions already have custom header."
        )

        expected_calls = [
            call.update_waf_acl(pending_secret["HEADERVALUE"], current_secret["HEADERVALUE"]),
            call.update_cf_distro("dist1", pending_secret["HEADERVALUE"]),
            call.update_cf_distro("dist2", pending_secret["HEADERVALUE"]),
        ]
        actual_calls = rotator.update_waf_acl.mock_calls + rotator.update_cf_distro.mock_calls
        assert actual_calls == expected_calls

    def test_some_distributions_missing_header(self, rotator):
        """
        Test scenario where some distributions are missing the custom header.

        Verify header is added and all distributions are updated.
        """
        mock_logger = MagicMock()
        rotator.logger = mock_logger

        matching_distributions = [{"Id": "dist1"}, {"Id": "dist2"}]
        pending_secret = {"HEADERVALUE": "new-secret"}
        current_secret = {"HEADERVALUE": "old-secret"}

        def mock_get_cf_distro_config(distro_id):
            if distro_id == "dist1":
                return {
                    "DistributionConfig": {
                        "Origins": {"Items": [{"Id": "origin1", "CustomHeaders": {"Items": []}}]}
                    }
                }
            return {
                "DistributionConfig": {
                    "Origins": {
                        "Items": [
                            {
                                "Id": "origin1",
                                "CustomHeaders": {
                                    "Items": [
                                        {
                                            "HeaderName": "x-origin-verify",
                                            "HeaderValue": "existing-secret",
                                        }
                                    ]
                                },
                            }
                        ]
                    }
                }
            }

        rotator.get_cf_distro_config = mock_get_cf_distro_config

        rotator.update_waf_acl = MagicMock()
        rotator.update_cf_distro = MagicMock()
        time.sleep = MagicMock()

        rotator.process_cf_distributions_and_WAF_rules(
            matching_distributions, pending_secret, current_secret
        )

        assert rotator.update_cf_distro.call_count == len(matching_distributions)
        for distro in matching_distributions:
            rotator.update_cf_distro.assert_any_call(distro["Id"], pending_secret["HEADERVALUE"])

        rotator.update_waf_acl.assert_called_once_with(
            pending_secret["HEADERVALUE"], current_secret["HEADERVALUE"]
        )

        assert time.sleep.call_count == 1

        mock_logger.info.assert_any_call(
            "Not all CloudFront distributions have the header. Updating WAF last."
        )

        expected_calls = [
            call.update_cf_distro("dist1", pending_secret["HEADERVALUE"]),
            call.update_cf_distro("dist2", pending_secret["HEADERVALUE"]),
            call.update_waf_acl(pending_secret["HEADERVALUE"], current_secret["HEADERVALUE"]),
        ]

        actual_calls = rotator.update_cf_distro.mock_calls + rotator.update_waf_acl.mock_calls
        assert actual_calls == expected_calls


class TestSecretManagement:
    """
    Tests for AWS Secrets Manager operations during rotation.

    Tests verify the creation and management of secrets during the rotation
    process.
    """

    def test_new_secret_created_when_no_pending_exists(self, rotator):
        """Create a new pending secret if none exists."""
        mock_service_client = MagicMock()
        mock_service_client.exceptions.ResourceNotFoundException = Exception

        def mock_get_secret_value(**kwargs):
            if kwargs["VersionStage"] == "AWSCURRENT":
                # Simulate AWSCURRENT exists
                return {"SecretString": json.dumps({"HEADERVALUE": "current-secret"})}
            elif kwargs["VersionStage"] == "AWSPENDING":
                # Simulate AWSPENDING does not exist
                raise mock_service_client.exceptions.ResourceNotFoundException(
                    {"Error": {"Code": "ResourceNotFoundException"}}, "GetSecretValue"
                )
            raise ValueError("Unexpected call to get_secret_value")

        mock_service_client.get_secret_value.side_effect = mock_get_secret_value

        mock_service_client.get_random_password.return_value = {"RandomPassword": "new-secret"}

        mock_service_client.put_secret_value.return_value = {}

        with patch("boto3.client", return_value=mock_service_client):
            rotator.create_secret(mock_service_client, "test-arn", "test-token")

        mock_service_client.get_secret_value.assert_has_calls(
            [
                call(SecretId="test-arn", VersionStage="AWSCURRENT"),  # First call for AWSCURRENT
                call(
                    SecretId="test-arn", VersionId="test-token", VersionStage="AWSPENDING"
                ),  # Second call for AWSPENDING
            ]
        )

        mock_service_client.put_secret_value.assert_called_once_with(
            SecretId="test-arn",
            ClientRequestToken="test-token",
            SecretString='{"HEADERVALUE": "new-secret"}',
            VersionStages=["AWSPENDING"],
        )

    def test_awscurrent_not_found_logs_error(self, rotator):
        """Test that a ResourceNotFoundException for AWSCURRENT logs the
        appropriate error message."""
        mock_logger = MagicMock()
        rotator.logger = mock_logger
        mock_service_client = MagicMock()

        mock_service_client.exceptions.ResourceNotFoundException = Exception

        # Configure the `get_secret_value` method to raise an exception for AWSCURRENT
        def mock_get_secret_value(**kwargs):
            if kwargs["VersionStage"] == "AWSCURRENT":
                raise mock_service_client.exceptions.ResourceNotFoundException(
                    {"Error": {"Code": "ResourceNotFoundException"}}, "GetSecretValue"
                )

            return {"SecretString": json.dumps({"HEADERVALUE": "current-secret"})}

        mock_service_client.get_secret_value.side_effect = mock_get_secret_value

        rotator.create_secret(mock_service_client, "test-arn", "test-token")

        mock_logger.error.assert_called_with("AWSCURRENT version does not exist for secret")


class TestRotationProcess:
    """
    Tests for the complete secret rotation process.

    Verifying the end-to-end rotation workflow and its components.
    """

    def test_set_secret_updates_waf_first_when_all_distributions_have_header(self, rotator):
        """The WAF ACL should be updated before the distributions when all
        distributions already have the header."""
        # Mock distributions
        mock_distributions = [
            {"Id": "DIST1", "Origin": "origin1.example.com"},
            {"Id": "DIST2", "Origin": "origin2.example.com"},
        ]

        mock_get_distro_with_header = {
            "DistributionConfig": {
                "Origins": {
                    "Items": [
                        {
                            "CustomHeaders": {
                                "Items": [
                                    {
                                        "HeaderName": rotator.header_name,
                                        "HeaderValue": "current-secret",
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }

        # Mock secrets and metadata
        mock_metadata = {
            "VersionIdsToStages": {"current-version": ["AWSCURRENT"], "test-token": ["AWSPENDING"]}
        }
        mock_credentials = {
            "Credentials": {
                "AccessKeyId": "test-access-key",
                "SecretAccessKey": "test-secret-key",
                "SessionToken": "test-session-token",
            }
        }
        mock_pending_secret = {"SecretString": json.dumps({"HEADERVALUE": "new-secret"})}
        mock_current_secret = {"SecretString": json.dumps({"HEADERVALUE": "current-secret"})}

        mock_boto_client = MagicMock()
        mock_boto_client.get_secret_value.side_effect = [mock_pending_secret, mock_current_secret]
        mock_boto_client.describe_secret.return_value = mock_metadata
        mock_boto_client.assume_role.return_value = mock_credentials

        time.sleep = MagicMock()
        rotator.is_distribution_deployed = MagicMock(return_value=True)
        rotator.get_cf_distro_config = MagicMock(return_value=mock_get_distro_with_header)
        rotator.update_cf_distro = MagicMock()
        rotator.update_waf_acl = MagicMock()
        rotator.get_deployed_distributions = MagicMock(return_value=mock_distributions)

        rotator.set_secret(mock_boto_client, "test-arn", "test-token")

        # Expect update_waf_acl to be called first with the new and current secret values
        rotator.update_waf_acl.assert_called_once_with("new-secret", "current-secret")

        # Ensure that update_cf_distro is called in the correct sequence
        rotator.update_cf_distro.assert_has_calls(
            [call("DIST1", "new-secret"), call("DIST2", "new-secret")], any_order=False
        )

        time.sleep.assert_called_once_with(rotator.waf_sleep_duration)

    def test_set_secret_updates_distributions_first_when_some_distributions_lack_header(
        self, rotator
    ):
        """Distributions should be updated first, and then the WAF ACL should be
        updated when some distributions are missing the header."""
        # Mock distributions
        mock_distributions = [
            {"Id": "DIST1", "Origin": "origin1.example.com"},
            {"Id": "DIST2", "Origin": "origin2.example.com"},
        ]

        mock_get_distro_without_header = {"DistributionConfig": {"Origins": {"Items": []}}}
        mock_get_distro_with_header = {
            "DistributionConfig": {
                "Origins": {
                    "Items": [
                        {
                            "CustomHeaders": {
                                "Items": [
                                    {
                                        "HeaderName": rotator.header_name,
                                        "HeaderValue": "current-secret",
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }

        # Mock secrets and metadata
        mock_metadata = {
            "VersionIdsToStages": {"current-version": ["AWSCURRENT"], "test-token": ["AWSPENDING"]}
        }
        mock_credentials = {
            "Credentials": {
                "AccessKeyId": "test-access-key",
                "SecretAccessKey": "test-secret-key",
                "SessionToken": "test-session-token",
            }
        }
        mock_pending_secret = {"SecretString": json.dumps({"HEADERVALUE": "new-secret"})}
        mock_current_secret = {"SecretString": json.dumps({"HEADERVALUE": "current-secret"})}

        # Mock boto3 client
        mock_boto_client = MagicMock()
        mock_boto_client.get_secret_value.side_effect = [mock_pending_secret, mock_current_secret]
        mock_boto_client.describe_secret.return_value = mock_metadata
        mock_boto_client.assume_role.return_value = mock_credentials

        time.sleep = MagicMock()
        rotator.is_distribution_deployed = MagicMock(return_value=True)
        rotator.get_cf_distro_config = MagicMock(
            side_effect=[
                mock_get_distro_without_header,  # DIST1
                mock_get_distro_with_header,  # DIST2
            ]
        )
        rotator.update_cf_distro = MagicMock()
        rotator.update_waf_acl = MagicMock()
        rotator.get_deployed_distributions = MagicMock(return_value=mock_distributions)

        rotator.set_secret(mock_boto_client, "test-arn", "test-token")

        rotator.update_cf_distro.assert_has_calls(
            [call("DIST1", "new-secret"), call("DIST2", "new-secret")], any_order=False
        )

        rotator.update_waf_acl.assert_called_once_with("new-secret", "current-secret")

        time.sleep.assert_called_once_with(rotator.waf_sleep_duration)

    def test_secret_validates_all_origins_with_both_secrets(self, rotator):
        """The test_secret phase must verify all origin servers accept both old
        and new secrets."""
        mock_distributions = [
            {"Id": "DIST1", "Domain": "domain1.example.com"},
            {"Id": "DIST2", "Domain": "domain2.example.com"},
        ]

        mock_pending_secret = {"SecretString": json.dumps({"HEADERVALUE": "new-secret"})}
        mock_current_secret = {"SecretString": json.dumps({"HEADERVALUE": "current-secret"})}
        mock_metadata = {
            "VersionIdsToStages": {"current-version": ["AWSCURRENT"], "test-token": ["AWSPENDING"]}
        }

        mock_service_client = MagicMock()
        mock_service_client.get_secret_value.side_effect = [
            mock_pending_secret,
            mock_current_secret,
        ]
        mock_service_client.describe_secret.return_value = mock_metadata

        rotator.get_deployed_distributions = MagicMock()
        rotator.get_deployed_distributions.return_value = mock_distributions

        rotator.run_test_origin_access = MagicMock()
        rotator.run_test_origin_access.return_value = True

        rotator.run_test_secret(mock_service_client, "test-arn", "test_token")

        expected_test_calls = [
            call("http://domain1.example.com", "new-secret"),
            call("http://domain1.example.com", "current-secret"),
            call("http://domain2.example.com", "new-secret"),
            call("http://domain2.example.com", "current-secret"),
        ]
        rotator.run_test_origin_access.assert_has_calls(expected_test_calls, any_order=True)


class TestFinishSecretStage:
    """Test final_secret stage moves the AWSPENDING secret to AWSCURRENT."""

    def test_finish_secret_completes_rotation(self, rotator):
        """
        finish_secret must properly complete the rotation by:
        1. Moving AWSPENDING to AWSCURRENT
        2. Removing AWSCURRENT from old version
        """
        mock_service_client = MagicMock()
        mock_service_client.describe_secret.return_value = {
            "VersionIdsToStages": {"old-version": ["AWSCURRENT"], "test-token": ["AWSPENDING"]}
        }

        rotator.finish_secret(mock_service_client, "test-arn", "test-token")

        mock_service_client.update_secret_version_stage.assert_called_once_with(
            SecretId="test-arn",
            VersionStage="AWSCURRENT",
            MoveToVersionId="test-token",
            RemoveFromVersionId="old-version",
        )

    def test_finish_secret_handles_no_previous_version(self, rotator):
        """When no AWSCURRENT version exists (first rotation), finish_secret
        should still complete successfully."""
        mock_service_client = MagicMock()
        mock_service_client.describe_secret.return_value = {
            "VersionIdsToStages": {"test-token": ["AWSPENDING"]}
        }

        rotator.finish_secret(mock_service_client, "test-arn", "test-token")

        mock_service_client.update_secret_version_stage.assert_called_once_with(
            SecretId="test-arn",
            VersionStage="AWSCURRENT",
            MoveToVersionId="test-token",
            RemoveFromVersionId=None,
        )

    def test_finish_secret_handles_api_errors(self, rotator):
        """finish_secret must handle AWS API errors gracefully."""
        mock_service_client = MagicMock()
        mock_service_client.describe_secret.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}}, "describe_secret"
        )

        with pytest.raises(ClientError) as exc_info:
            rotator.finish_secret(mock_service_client, "test-arn", "test-token")

        assert exc_info.value.response["Error"]["Code"] == "ResourceNotFoundException"
        mock_service_client.update_secret_version_stage.assert_not_called()


class TestErrorHandling:
    """Tests for error handling throughout the rotation process."""

    def test_fails_early_if_distribution_not_deployed(self, rotator):
        """If any distribution is not in 'Deployed' state, the entire rotation
        must fail before making any changes."""
        mock_distributions = [
            {"Id": "DIST1", "Origin": "origin1.example.com"},
            {"Id": "DIST2", "Origin": "origin2.example.com"},
        ]

        mock_service_client = MagicMock()

        rotator.get_deployed_distributions = MagicMock()
        rotator.get_deployed_distributions.return_value = mock_distributions

        rotator.is_distribution_deployed = MagicMock(
            side_effect=lambda distro_id: distro_id == "DIST1"
        )

        rotator.update_waf_acl = MagicMock()

        with pytest.raises(ValueError) as exc_info:
            rotator.set_secret(mock_service_client, "test-arn", "test_token")

        assert "status is not Deployed" in str(exc_info.value)
        rotator.update_waf_acl.assert_not_called()

    def test_handles_waf_update_failure_without_distribution_updates(self, rotator):
        """If WAF update fails, no distribution updates should occur."""
        mock_distributions = [{"Id": "DIST1", "Origin": "origin1.example.com"}]
        mock_get_distro = {"Distribution": {"Status": "Deployed"}}

        mock_pending_secret = {"SecretString": json.dumps({"HEADERVALUE": "AWSPENDING"})}
        mock_current_secret = {"SecretString": json.dumps({"HEADERVALUE": "AWSCURRENT"})}

        mock_service_client = MagicMock()
        mock_service_client.describe_secret.return_value = {
            "VersionIdsToStages": mock_current_secret
        }

        mock_service_client.get_secret_value.side_effect = [
            mock_pending_secret,  # For AWSPENDING
            mock_current_secret,  # For AWSCURRENT
        ]

        rotator.get_deployed_distributions = MagicMock()
        rotator.get_deployed_distributions.return_value = mock_distributions

        rotator.get_cf_distro = MagicMock()
        rotator.get_cf_distro.return_value = mock_get_distro

        rotator.update_cf_distro = MagicMock()
        rotator.process_cf_distributions_and_WAF_rules = MagicMock()

        rotator.process_cf_distributions_and_WAF_rules.side_effect = ClientError(
            {"Error": {"Code": "WAFInvalidParameterException"}},
            "process_cf_distributions_and_WAF_rules",
        )

        with pytest.raises(ValueError):
            rotator.set_secret(mock_service_client, "test-arn", "test_token")

            # Ensure no CloudFront distribution updates occur
            rotator.update_cf_distro.assert_not_called()


class TestEdgeCases:

    def test_handles_empty_distribution_list_gracefully(self, rotator):
        """
        When no matching distributions are found:
        1. WAF rules should not be updated.
        2. Distribution updates should not be attempted.
        3. The method should raise an error and stop.
        """
        mock_pending_secret = {"SecretString": json.dumps({"HEADERVALUE": "new-secret"})}
        mock_current_secret = {"SecretString": json.dumps({"HEADERVALUE": "current-secret"})}
        mock_metadata = {
            "VersionIdsToStages": {
                "current-version": ["AWSCURRENT"],
                "test-token": ["AWSPENDING"],
            }
        }
        mock_credentials = {
            "Credentials": {
                "AccessKeyId": "test-access-key",
                "SecretAccessKey": "test-secret-key",
                "SessionToken": "test-session-token",
            }
        }

        rotator.get_deployed_distributions = MagicMock()
        rotator.get_deployed_distributions.return_value = []

        mock_boto_client = MagicMock()
        mock_boto_client.assume_role.return_value = mock_credentials
        mock_boto_client.get_secret_value.side_effect = [
            mock_pending_secret,  # For AWSPENDING
            mock_current_secret,  # For AWSCURRENT
        ]
        mock_boto_client.describe_secret.return_value = mock_metadata

        rotator.get_waf_acl = MagicMock()
        rotator.update_cf_distro = MagicMock()
        time.sleep = MagicMock()

        with pytest.raises(
            ValueError,
            match="No matching distributions found. Cannot update Cloudfront distributions or WAF ACLs",
        ):
            rotator.set_secret(mock_boto_client, "test-arn", "token")

        rotator.get_waf_acl.assert_not_called()
        rotator.update_cf_distro.assert_not_called()
        time.sleep.assert_not_called()

    def test_handles_malformed_secret_data(self, rotator):
        mock_service_client = MagicMock()
        mock_service_client.get_secret_value.return_value = {"SecretString": "invalid-json"}

        with pytest.raises(ValueError):
            rotator.run_test_secret(mock_service_client, "test-arn", "test-token")


class TestLambdaHandler:

    def test_executes_correct_rotation_step(self):
        """Lambda must execute the correct rotation step based on the event."""
        event = {"SecretId": "test-arn", "ClientRequestToken": "test-token", "Step": "createSecret"}

        mock_rotator = MagicMock()
        mock_boto_client = MagicMock()

        with patch("boto3.client", return_value=mock_boto_client):
            with patch("rotate_secret_lambda.SecretRotator", return_value=mock_rotator):

                from rotate_secret_lambda import lambda_handler

                lambda_handler(event, None)

                mock_rotator.create_secret.assert_called_once_with(
                    mock_boto_client, "test-arn", "test-token"
                )

    def test_run_test_secret_with_test_domains(self, rotator):
        """Tests the testSecret step in the event."""
        event = {
            "SecretId": "test-arn",
            "ClientRequestToken": "test-token",
            "Step": "testSecret",
            "TestDomains": ["domain1.example.com", "domain2.example.com"],
        }
        mock_distributions = [
            {"Id": "DIST1", "Origin": "domain1.example.com"},
            {"Id": "DIST2", "Origin": "domain2.example.com"},
        ]

        mock_pending_secret = {"SecretString": json.dumps({"HEADERVALUE": "new-secret"})}

        mock_current_secret = {"SecretString": json.dumps({"HEADERVALUE": "current-secret"})}

        mock_metadata = {
            "RotationEnabled": True,
            "VersionIdsToStages": {"current-token": ["AWSCURRENT"], "test-token": ["AWSPENDING"]},
        }

        mock_boto_client = MagicMock()
        mock_boto_client.describe_secret.return_value = mock_metadata
        mock_boto_client.get_secret_value.side_effect = [mock_pending_secret, mock_current_secret]

        rotator.get_deployed_distributions = MagicMock()
        rotator.get_deployed_distributions.return_value = mock_distributions

        with patch("boto3.client") as mock_boto_client, patch(
            "rotate_secret_lambda.SecretRotator"
        ) as mock_rotator:

            mock_rotator_instance = mock_rotator.return_value

            from rotate_secret_lambda import lambda_handler

            lambda_handler(event, None)

            actual_calls = mock_rotator_instance.run_test_secret.call_args_list

            assert (
                len(actual_calls) == 1
            ), f"Expected run_test_secret to be called once, but it was called {mock_rotator_instance.run_test_secret.call_count} times."

            call_args = actual_calls[0][0]
            for i, arg in enumerate(call_args):
                assert call_args[1] == "test-arn"
                assert call_args[2] == "test-token"
                assert call_args[3] == ["domain1.example.com", "domain2.example.com"]

    def test_run_test_secret_triggers_slack_message(self, rotator):
        """
        Tests the testSecret step with a TestDomains property in the event.

        Verifies that slack notifications are triggered for test failures.
        """
        test_domains = [
            "invalidservice1.environment.testapp.domain.digital",
            "invalidservice2.environment.testapp.domain.digital",
        ]

        mock_slack_instance = MagicMock()
        rotator.slack_service = mock_slack_instance

        rotator.run_test_secret(
            service_client=MagicMock(),
            arn="test-arn",
            token="test-token",
            test_domains=test_domains,
        )

        expected_failures = [
            {
                "domain": "invalidservice1.environment.testapp.domain.digital",
                "error": "Simulating test failure for domain: http://invalidservice1.environment.testapp.domain.digital",
            },
            {
                "domain": "invalidservice2.environment.testapp.domain.digital",
                "error": "Simulating test failure for domain: http://invalidservice2.environment.testapp.domain.digital",
            },
        ]

        mock_slack_instance.send_test_failures.assert_called_once_with(
            failures=expected_failures,
            environment=rotator.environment,
            application=rotator.application,
        )
