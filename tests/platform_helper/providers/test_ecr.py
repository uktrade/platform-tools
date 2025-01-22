from datetime import datetime
from unittest.mock import Mock

from dbt_platform_helper.providers.ecr import ECRProvider


def test_aws_get_ecr_repos_success():
    mock_session = Mock()
    mock_client = Mock()
    mock_session.client.return_value = mock_client
    mock_client.describe_repositories.return_value = {
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
                "repositoryArn": "arn:aws:ecr:eu-west-2:12345:repository/test-app/codebase_2",
                "repositoryName": "test-app/codebase_2",
                "repositoryUri": "12345.dkr.ecr.eu-west-2.amazonaws.com/test-app/codebase_2",
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
    }

    aws_provider = ECRProvider(mock_session)
    repositories = aws_provider.get_ecr_repo_names()

    mock_session.client.assert_called_once_with("ecr")
    assert len(repositories) == 3
    assert "test-app/codebase_1" in repositories
    assert "test-app/codebase_2" in repositories
    assert "some-other-repo" in repositories
