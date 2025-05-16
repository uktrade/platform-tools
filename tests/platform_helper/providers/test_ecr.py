from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import Mock

import botocore
import pytest

from dbt_platform_helper.providers.aws.exceptions import ImageNotFoundException
from dbt_platform_helper.providers.aws.exceptions import RepositoryNotFoundException
from dbt_platform_helper.providers.ecr import NO_ASSOCIATED_COMMIT_TAG_WARNING
from dbt_platform_helper.providers.ecr import NOT_A_UNIQUE_TAG_INFO
from dbt_platform_helper.providers.ecr import ECRProvider
from dbt_platform_helper.utils.application import Application


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


image_id_pages = {
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
            {"imageDigest": "sha256:777", "imageTag": "branch-across-pages"},
        ],
    },
}


def return_image_pages(**kwargs):
    token = kwargs.get("nextToken", "page_1")
    return image_id_pages[token]


@pytest.mark.parametrize(
    "test_name, reference, expected_tag, expect_info_message",
    [
        ("commit page 1", "commit-09dc178af5", "commit-09dc178af5", False),
        ("branch page 2", "branch-fix-truncation-error", "commit-76e34", True),
        ("tag page 3", "tag-1.2.3", "commit-79dc178af5", True),
        ("single match commit", "commit-73ee4f5123abc", "commit-73ee4f5", False),
        ("cross page commit", "commit-23ee4f5", "commit-23ee4f5", False),
        ("cross page branch", "branch-across-pages", "commit-23ee4f5", True),
        ("cross page tag", "tag-across-pages", "commit-23ee4f5", True),
    ],
)
def test_get_commit_tag_for_reference(test_name, reference, expected_tag, expect_info_message):
    session_mock = Mock()
    client_mock = Mock()
    session_mock.client.return_value = client_mock
    client_mock.list_images.side_effect = return_image_pages
    mock_io = Mock()

    ecr_provider = ECRProvider(session_mock, mock_io)

    actual = ecr_provider.get_commit_tag_for_reference("test_app", "test_codebase", reference)

    assert actual == expected_tag, f"'{test_name}' test case failed"
    if expect_info_message:
        mock_io.info.assert_called_once_with(
            NOT_A_UNIQUE_TAG_INFO.format(image_ref=reference, commit_tag=expected_tag)
        )


def test_get_commit_tag_for_reference_falls_back_on_non_commit_tag_with_warning():
    session_mock = Mock()
    client_mock = Mock()
    session_mock.client.return_value = client_mock
    client_mock.list_images.return_value = image_id_pages["page_3"]
    mock_io = Mock()

    ecr_provider = ECRProvider(session_mock, mock_io)

    reference = "branch-across-pages"
    actual = ecr_provider.get_commit_tag_for_reference("test_app", "test_codebase", reference)

    assert actual == reference
    mock_io.warn.assert_called_once_with(
        NO_ASSOCIATED_COMMIT_TAG_WARNING.format(image_ref=reference)
    )


def test_get_commit_tag_for_reference_errors_when_no_images_match():
    pass


def test_get_commit_tag_for_reference_errors_when_multiple_images_match():
    pass


def test_get_commit_tag_for_reference_recasts_exceptions_as_platform_exceptions():
    pass


def test_get_image_details_returns_details():
    session_mock = MagicMock()
    client_mock = MagicMock()
    session_mock.client.return_value = client_mock
    image_info = {"imageDetails": [{"imageTags": ["tag-4.2.0", "commit-ab1c23d", "latest"]}]}
    client_mock.describe_images.return_value = image_info
    ecr = ECRProvider(session_mock)

    image_details_retrieved = ecr.get_image_details(
        Application(name="test_application"), "test_codebase", "commit-ab1c23d"
    )
    assert image_details_retrieved == [{"imageTags": ["tag-4.2.0", "commit-ab1c23d", "latest"]}]
    client_mock.describe_images.assert_called_once_with(
        repositoryName="test_application/test_codebase", imageIds=[{"imageTag": "commit-ab1c23d"}]
    )


def test_get_image_details_raises_image_details_not_found_when_there_are_no_image_details():
    session_mock = MagicMock()
    client_mock = MagicMock()
    session_mock.client.return_value = client_mock
    image_info = {}
    client_mock.describe_images.return_value = image_info
    ecr = ECRProvider(session_mock)

    with pytest.raises(ImageNotFoundException) as exception_info:
        ecr.get_image_details(
            Application(name="test_application"), "test_codebase", "commit-ab1c23d"
        )

    actual_error = str(exception_info.value)
    expected_error = 'An image labelled "commit-ab1c23d" could not be found in your image repository. Try the `platform-helper codebase build` command first.'

    assert actual_error == expected_error


def test_get_image_details_raises_image_not_found():
    session_mock = MagicMock()
    client_mock = MagicMock()
    session_mock.client.return_value = client_mock
    client_mock.describe_images.side_effect = botocore.exceptions.ClientError(
        {
            "Error": {"Code": "ImageNotFoundException"},
        },
        operation_name="DescribeImages",
    )

    ecr = ECRProvider(session_mock)

    with pytest.raises(ImageNotFoundException) as exception_info:
        ecr.get_image_details(
            Application(name="test_application"), "test_codebase", "commit-ab1c23d"
        )

    actual_error = str(exception_info.value)
    expected_error = 'An image labelled "commit-ab1c23d" could not be found in your image repository. Try the `platform-helper codebase build` command first.'

    assert actual_error == expected_error


def test_get_image_details_raises_repository_not_found():
    session_mock = MagicMock()
    client_mock = MagicMock()
    session_mock.client.return_value = client_mock
    client_mock.describe_images.side_effect = botocore.exceptions.ClientError(
        {
            "Error": {"Code": "RepositoryNotFoundException"},
        },
        operation_name="DescribeImages",
    )

    ecr = ECRProvider(session_mock)

    with pytest.raises(RepositoryNotFoundException) as exception_info:
        ecr.get_image_details(
            Application(name="test_application"), "test_codebase", "commit-ab1c23d"
        )

    actual_error = str(exception_info.value)
    expected_error = 'The ECR repository "test_application/test_codebase" could not be found.'

    assert actual_error == expected_error


def test_find_commit_tag_returns_commit_tag_from_image_details():
    ecr = ECRProvider(Mock(), Mock())
    image_details = [{"imageTags": ["tag-1.2.3", "branch-main", "commit-abc123"]}]
    actual_tag = ecr.find_commit_tag(image_details, "tag-1.2.3")

    ecr.click_io.info.assert_called_once_with(
        'INFO: The tag "tag-1.2.3" is not a unique, commit-specific tag. Deploying the corresponding commit tag "commit-abc123" instead.'
    )
    assert actual_tag == "commit-abc123"


@pytest.mark.parametrize(
    "image_details",
    [
        None,
        [],
        [{}],
        [{"imageDetails": None}],
        [{"imageDetails": [{"imageTags": ["commit-987zxy"]}]}],
    ],
)
def test_find_commit_tag_returns_commit_tag_from_a_commit_tag_ignoring_image_details(image_details):
    ecr = ECRProvider(Mock(), Mock())

    actual_tag = ecr.find_commit_tag(image_details, "commit-abc123")

    ecr.click_io.info.assert_not_called()
    ecr.click_io.warn.assert_not_called()
    assert actual_tag == "commit-abc123"


def test_find_commit_tag_returns_the_original_ref_if_no_commit_tag():
    ecr = ECRProvider(Mock(), Mock())

    image_details = [{"imageTags": ["tag-1.2.3", "branch-main"]}]

    actual_tag = ecr.find_commit_tag(image_details, "tag-1.2.3")

    ecr.click_io.warn.assert_called_once_with(
        'WARNING: The AWS ECR image "tag-1.2.3" has no associated commit tag so deploying "tag-1.2.3". Note this could result in images with unintended or incompatible changes being deployed if new ECS Tasks for your service.'
    )
    assert actual_tag == "tag-1.2.3"


@pytest.mark.parametrize(
    "image_details",
    [
        None,
        [],
        [{}],
        [{"imageDetails": None}],
        [{"imageDetails": []}],
    ],
)
def test_find_commit_tag_handles_malformed_image_details(image_details):
    ecr = ECRProvider(Mock(), Mock())

    actual_tag = ecr.find_commit_tag(image_details, "tag-1.2.3")

    ecr.click_io.warn.assert_called_once_with(
        'WARNING: The AWS ECR image "tag-1.2.3" has no associated commit tag so deploying "tag-1.2.3". Note this could result in images with unintended or incompatible changes being deployed if new ECS Tasks for your service.'
    )
    assert actual_tag == "tag-1.2.3"
