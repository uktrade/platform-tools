from datetime import datetime
from unittest.mock import Mock

import botocore
import pytest

from dbt_platform_helper.providers.aws.exceptions import IMAGE_NOT_FOUND_TEMPLATE
from dbt_platform_helper.providers.aws.exceptions import MULTIPLE_IMAGES_FOUND_TEMPLATE
from dbt_platform_helper.providers.aws.exceptions import REPOSITORY_NOT_FOUND_TEMPLATE
from dbt_platform_helper.providers.aws.exceptions import AWSException
from dbt_platform_helper.providers.aws.exceptions import ImageNotFoundException
from dbt_platform_helper.providers.aws.exceptions import MultipleImagesFoundException
from dbt_platform_helper.providers.aws.exceptions import RepositoryNotFoundException
from dbt_platform_helper.providers.ecr import NO_ASSOCIATED_COMMIT_TAG_WARNING
from dbt_platform_helper.providers.ecr import NOT_A_UNIQUE_TAG_INFO
from dbt_platform_helper.providers.ecr import ECRProvider


class ECRProviderMocks:
    def __init__(self):
        self.session_mock = Mock()
        self.client_mock = Mock()
        self.session_mock.client.return_value = self.client_mock
        self.mock_io = Mock()

    def params(self):
        return {"session": self.session_mock, "click_io": self.mock_io}


def test_aws_get_ecr_repos_success(two_pages_of_describe_repository_data):
    mock_session = Mock()
    mock_session.client.return_value.get_paginator.return_value.paginate.return_value = (
        two_pages_of_describe_repository_data
    )
    aws_provider = ECRProvider(mock_session)

    repositories = aws_provider.get_ecr_repo_names()

    mock_session.client.assert_called_once_with("ecr")
    mock_session.client().get_paginator.assert_called_once_with("describe_repositories")
    mock_session.client().get_paginator().paginate.assert_called_once()
    assert len(repositories) == 3
    assert "test-app/codebase_1" in repositories
    assert "test-app/codebase_2" in repositories
    assert "some-other-repo" in repositories


@pytest.fixture
def two_pages_of_describe_repository_data():
    return [
        {
            "ResponseMetadata": {
                "HTTPHeaders": {
                    "connection": "keep-alive",
                    "content-length": "10239",
                    "content-type": "application/x-amz-json-1.1",
                    "date": "Mon, 20 Jan 2025 16:23:59 GMT",
                    "x-amzn-requestid": "1234567890a-40d9-9871-abcdef123456",
                },
                "HTTPStatusCode": 200,
                "RequestId": "1234567890a-40d9-9871-abcdef123456",
                "RetryAttempts": 0,
            },
            "repositories": [
                {
                    "createdAt": datetime(2024, 5, 23, 16, 29, 16, 87000),
                    "encryptionConfiguration": {"encryptionType": "AES256"},
                    "imageScanningConfiguration": {"scanOnPush": False},
                    "imageTagMutability": "MUTABLE",
                    "registryId": "12345",
                    "repositoryArn": "arn:aws:ecr:eu-west-2:12345:repository/test-app/codebase_1",
                    "repositoryName": "test-app/codebase_1",
                    "repositoryUri": "12345.dkr.ecr.eu-west-2.amazonaws.com/test-app/codebase_1",
                },
                {
                    "createdAt": datetime(2024, 12, 3, 15, 39, 34, 353000),
                    "encryptionConfiguration": {"encryptionType": "AES256"},
                    "imageScanningConfiguration": {"scanOnPush": False},
                    "imageTagMutability": "MUTABLE",
                    "registryId": "12345",
                    "repositoryArn": "arn:aws:ecr:eu-west-2:12345:repository/some-other-repo",
                    "repositoryName": "some-other-repo",
                    "repositoryUri": "12345.dkr.ecr.eu-west-2.amazonaws.com/some-other-repo",
                },
            ],
        },
        {
            "ResponseMetadata": {
                "HTTPHeaders": {
                    "connection": "keep-alive",
                    "content-length": "10239",
                    "content-type": "application/x-amz-json-1.1",
                    "date": "Mon, 20 Jan 2025 16:23:59 GMT",
                    "x-amzn-requestid": "1234567890a-40d9-9871-abcdef123456",
                },
                "HTTPStatusCode": 200,
                "RequestId": "1234567890a-40d9-9871-abcdef123456",
                "RetryAttempts": 0,
            },
            "repositories": [
                {
                    "createdAt": datetime(2024, 12, 3, 15, 39, 34, 353000),
                    "encryptionConfiguration": {"encryptionType": "AES256"},
                    "imageScanningConfiguration": {"scanOnPush": False},
                    "imageTagMutability": "MUTABLE",
                    "registryId": "12345",
                    "repositoryArn": "arn:aws:ecr:eu-west-2:12345:repository/test-app/codebase_2",
                    "repositoryName": "test-app/codebase_2",
                    "repositoryUri": "12345.dkr.ecr.eu-west-2.amazonaws.com/test-app/codebase_2",
                },
            ],
        },
    ]


IMAGE_ID_PAGES = {
    "page_1": {
        "imageIds": [
            {"imageDigest": "sha256:113", "imageTag": "commit-86e54f"},
            {"imageDigest": "sha256:114", "imageTag": "commit-56e34"},
            {"imageDigest": "sha256:114", "imageTag": "tag-1.2.3"},
            {"imageDigest": "sha256:777", "imageTag": "commit-23ee4f5"},
            {"imageDigest": "sha256:116", "imageTag": "commit-09dc178af5"},
        ],
        "nextToken": "page_2",
    },
    "page_2": {
        "imageIds": [
            {"imageDigest": "sha256:123", "imageTag": "commit-55e54f"},
            {"imageDigest": "sha256:124", "imageTag": "commit-55e34"},
            {"imageDigest": "sha256:134", "imageTag": "branch-fix-truncation-error"},
            {"imageDigest": "sha256:777", "imageTag": "tag-across-pages"},
            {"imageDigest": "sha256:125", "imageTag": "commit-55ee4f5"},
            {"imageDigest": "sha256:134", "imageTag": "commit-76e34"},
            {"imageDigest": "sha256:126", "imageTag": "commit-55dc178af5"},
        ],
        "nextToken": "page_3",
    },
    "page_3": {
        "imageIds": [
            {"imageDigest": "sha256:135", "imageTag": "commit-73ee4f5"},
            {"imageDigest": "sha256:136", "imageTag": "commit-79dc178af5"},
            {"imageDigest": "sha256:136", "imageTag": "tag-1.2.3"},
            {"imageDigest": "sha256:000", "imageTag": "tag-no-associated-commit"},
            {"imageDigest": "sha256:001", "imageTag": "branch-no-associated-commit"},
            {"imageDigest": "sha256:777", "imageTag": "branch-across-pages"},
            {"imageDigest": "sha256:887", "imageTag": "commit-deadbea7"},
            {"imageDigest": "sha256:888", "imageTag": "commit-deadbe"},
            {"imageDigest": "sha256:889", "imageTag": "commit-dead"},
        ],
    },
}


def return_image_pages(**kwargs):
    token = kwargs.get("nextToken", "page_1")
    return IMAGE_ID_PAGES[token]


@pytest.mark.parametrize(
    "test_name, reference, expected_tag, expect_info_message",
    [
        ("commit page 1", "commit-09dc178af5", "commit-09dc178af5", False),
        ("branch page 2", "branch-fix-truncation-error", "commit-76e34", True),
        ("tag page 3", "tag-1.2.3", "commit-79dc178af5", True),
        (
            "single match commit match less specific commit",
            "commit-73ee4f5123abc",
            "commit-73ee4f5",
            False,
        ),
        (
            "single match commit match more specific commit",
            "commit-55dc178",
            "commit-55dc178af5",
            False,
        ),
        ("cross page commit", "commit-23ee4f5", "commit-23ee4f5", False),
        ("cross page branch", "branch-across-pages", "commit-23ee4f5", True),
        ("cross page tag", "tag-across-pages", "commit-23ee4f5", True),
    ],
)
def test_get_commit_tag_for_reference(test_name, reference, expected_tag, expect_info_message):
    mocks = ECRProviderMocks()
    mocks.client_mock.list_images.side_effect = return_image_pages

    ecr_provider = ECRProvider(**mocks.params())

    actual = ecr_provider.get_commit_tag_for_reference("test_app", "test_codebase", reference)

    assert actual == expected_tag, f"'{test_name}' test case failed"
    if expect_info_message:
        mocks.mock_io.info.assert_called_once_with(
            NOT_A_UNIQUE_TAG_INFO.format(image_ref=reference, commit_tag=expected_tag)
        )


@pytest.mark.parametrize("reference", ["branch-no-associated-commit", "tag-no-associated-commit"])
def test_get_commit_tag_for_reference_falls_back_on_non_commit_tag_with_warning(reference):
    mocks = ECRProviderMocks()
    mocks.client_mock.list_images.return_value = IMAGE_ID_PAGES["page_3"]

    ecr_provider = ECRProvider(**mocks.params())

    actual = ecr_provider.get_commit_tag_for_reference("test_app", "test_codebase", reference)

    assert actual == reference
    mocks.mock_io.warn.assert_called_once_with(
        NO_ASSOCIATED_COMMIT_TAG_WARNING.format(image_ref=reference)
    )


@pytest.mark.parametrize(
    "reference", ["commit-abc123", "tag-no-such-tag", "branch-no-such-branch", "commit-z"]
)
def test_get_commit_tag_for_reference_errors_when_no_images_match(reference):
    mocks = ECRProviderMocks()
    mocks.client_mock.list_images.return_value = IMAGE_ID_PAGES["page_3"]
    ecr_provider = ECRProvider(**mocks.params())

    with pytest.raises(ImageNotFoundException) as ex:
        ecr_provider.get_commit_tag_for_reference("test_app", "test_codebase", reference)

    actual_error = str(ex.value)
    expected_error = IMAGE_NOT_FOUND_TEMPLATE.format(image_ref=reference)

    assert actual_error == expected_error


@pytest.mark.parametrize(
    "reference, expected_matches",
    [
        ("commit-deadbea7e", "commit-dead, commit-deadbe, commit-deadbea7"),
        ("commit-deadbea", "commit-dead, commit-deadbe, commit-deadbea7"),
    ],
)
def test_get_commit_tag_for_reference_errors_when_multiple_images_match(
    reference, expected_matches
):
    mocks = ECRProviderMocks()
    mocks.client_mock.list_images.return_value = IMAGE_ID_PAGES["page_3"]
    ecr_provider = ECRProvider(**mocks.params())

    with pytest.raises(MultipleImagesFoundException) as ex:
        ecr_provider.get_commit_tag_for_reference("test_app", "test_codebase", reference)

    actual_error = str(ex.value)
    expected_error = MULTIPLE_IMAGES_FOUND_TEMPLATE.format(
        image_ref=reference, matching_images=expected_matches
    )

    assert actual_error == expected_error


@pytest.mark.parametrize(
    "boto_exception, expected_exception, expected_message",
    [
        (
            "RepositoryNotFoundException",
            RepositoryNotFoundException,
            REPOSITORY_NOT_FOUND_TEMPLATE.format(repository="test_app/test_codebase"),
        ),
        (
            "SomeOtherException",
            AWSException,
            "Unexpected error for repo 'test_app/test_codebase' and image reference 'commit-abc123': "
            "An error occurred (SomeOtherException) when calling the ListImages operation: Unknown",
        ),
    ],
)
def test_get_commit_tag_for_reference_recasts_exceptions_as_more_specific_exceptions(
    boto_exception, expected_exception, expected_message
):
    mocks = ECRProviderMocks()
    mocks.client_mock.list_images.side_effect = botocore.exceptions.ClientError(
        {
            "Error": {"Code": boto_exception},
        },
        operation_name="ListImages",
    )

    ecr_provider = ECRProvider(**mocks.params())

    with pytest.raises(expected_exception) as ex:
        ecr_provider.get_commit_tag_for_reference("test_app", "test_codebase", "commit-abc123")

    actual_error = str(ex.value)
    expected_error = expected_message

    assert actual_error == expected_error
