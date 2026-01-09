import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import create_autospec
from unittest.mock import patch

import hcl2
import pytest
import yaml
from freezegun import freeze_time

from dbt_platform_helper.domain.pipelines import Pipelines
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.entities.semantic_version import SemanticVersion
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.ecr import ECRProvider
from dbt_platform_helper.providers.version import InstalledVersionProvider


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


class Mocks:
    def __init__(
        self,
        # has_access={"all": True},
        # put_parameter_unexpected=False,
        # create_existing_params="none",
    ):
        self.mocks = None

    def setup_generate(self, two_pages_of_describe_repository_data):

        self.mock_io = MagicMock()
        self.mock_installed_version_provider = create_autospec(
            spec=InstalledVersionProvider, spec_set=True
        )
        self.mock_installed_version_provider.get_semantic_version.return_value = SemanticVersion(
            14, 0, 0
        )
        self.mock_platform_helper_versioning = create_autospec(
            spec=PlatformHelperVersioning, spec_set=True
        )
        self.mock_platform_helper_versioning.check_platform_helper_version_mismatch.return_value = (
            None
        )
        self.mock_platform_helper_versioning.get_template_version.return_value = "14.0.0"
        self.mock_platform_helper_versioning.get_codebase_pipeline_modules_source.return_value = "git::git@github.com:uktrade/platform-tools.git//terraform/codebase-pipelines?depth=1&ref="
        self.mock_config_validator = Mock(spec=ConfigValidator)
        self.mock_config_provider = ConfigProvider(
            self.mock_config_validator,
            installed_version_provider=self.mock_installed_version_provider,
        )
        self.mock_git_remote = Mock()
        self.mock_git_remote.return_value = "uktrade/test-app-deploy"

        mock_session = Mock()
        mock_session.client.return_value.get_paginator.return_value.paginate.return_value = (
            two_pages_of_describe_repository_data
        )
        self.mock_ecr = ECRProvider(session=mock_session, click_io=self.mock_io)

        # self._create_sessions()

        return dict(
            config_provider=self.mock_config_provider,
            io=self.mock_io,
            get_git_remote=self.mock_git_remote,
            ecr_provider=self.mock_ecr,
            platform_helper_versioning=self.mock_platform_helper_versioning,
        )


@patch(
    "dbt_platform_helper.jinja2_tags.version", return_value="14.0.0"
)  # Fakefs breaks the metadata to retrieve package version
@patch("dbt_platform_helper.providers.terraform_manifest.version", return_value="14.0.0")
@freeze_time("2025-01-16 13:00:00")
def test_pipelines_generate(
    mock_version,
    mock_version_2,
    fakefs,
    create_valid_platform_config_file,
    two_pages_of_describe_repository_data,
):

    pipelines = Pipelines(**Mocks().setup_generate(two_pages_of_describe_repository_data))

    pipelines.generate(None)

    expected_file_path = Path("/terraform/codebase-pipelines/main.tf.json")
    assert expected_file_path.exists()

    # TODO check data in expected_file_path.read_text()

    # assert False


@patch(
    "dbt_platform_helper.jinja2_tags.version", return_value="14.0.0"
)  # Fakefs breaks the metadata to retrieve package version
@patch("dbt_platform_helper.providers.terraform_manifest.version", return_value="14.0.0")
@freeze_time("2025-01-16 13:00:00")
def test_pipelines_generate_workspaced(
    mock_version,
    mock_version_2,
    fakefs,
    valid_platform_config,
    two_pages_of_describe_repository_data,
):

    fakefs.create_file(
        Path("platform-config.workspace.yml"), contents=yaml.dump(valid_platform_config)
    )

    pipelines = Pipelines(**Mocks().setup_generate(two_pages_of_describe_repository_data))

    pipelines.generate(None, workspace="workspace")

    expected_cb_file_path = Path("/terraform/codebase-pipelines/main.tf.json")
    expected_env_np_file_path = Path("/terraform/environment-pipelines/non-prod-acc/main.tf")
    expected_env_p_file_path = Path("/terraform/environment-pipelines/prod-acc/main.tf")

    assert expected_cb_file_path.exists()
    assert expected_env_np_file_path.exists()
    assert expected_env_p_file_path.exists()

    def check_platform_config_path(file_path, plat_path):

        if file_path.suffix == ".json":
            content = file_path.read_text()
            json_content = json.loads(content)
            local = json_content["locals"]
        else:
            with open(file_path, "r") as file:
                json_content = hcl2.load(file)
                local = json_content["locals"]
                local = local[0]

        assert local["platform_config"] == f'${{yamldecode(file("{plat_path}"))}}'

    check_platform_config_path(expected_cb_file_path, "../../platform-config.workspace.yml")
    check_platform_config_path(expected_env_np_file_path, "../../../platform-config.workspace.yml")
    check_platform_config_path(expected_env_p_file_path, "../../../platform-config.workspace.yml")
