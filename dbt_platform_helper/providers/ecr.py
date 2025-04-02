import botocore
from boto3 import Session

from dbt_platform_helper.providers.aws.exceptions import ImageNotFoundException
from dbt_platform_helper.providers.aws.exceptions import RepositoryNotFoundException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.aws import get_aws_session_or_abort


class ECRProvider:
    def __init__(self, session: Session = None, click_io: ClickIOProvider = ClickIOProvider()):
        self.session = session
        self.click_io = click_io

    def get_ecr_repo_names(self) -> list[str]:
        out = []
        for page in self._get_client().get_paginator("describe_repositories").paginate():
            out.extend([repo["repositoryName"] for repo in page.get("repositories", {})])
        return out

    def get_image_details(
        self, application: Application, codebase: str, image_ref: str
    ) -> list[dict]:
        """Check if image exists in AWS ECR, and return a list of dictionaries
        containing image metadata."""

        repository = f"{application.name}/{codebase}"

        try:
            image_info = self._get_client().describe_images(
                repositoryName=repository,
                imageIds=[{"imageTag": image_ref}],
            )

            self._check_image_details_exists(image_info, image_ref)

            return image_info.get("imageDetails")
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "ImageNotFoundException":
                raise ImageNotFoundException(image_ref)
            if e.response["Error"]["Code"] == "RepositoryNotFoundException":
                raise RepositoryNotFoundException(repository)

    def find_commit_tag(self, image_details: list[dict], image_ref: str) -> str:
        """Loop through imageTags list to query for an image tag starting with
        'commit-', and return that value if found."""

        if image_ref.startswith("commit-"):
            return image_ref

        if image_details:
            for image in image_details:
                image_tags = image.get("imageTags", {})
                for tag in image_tags:
                    if tag.startswith("commit-"):
                        self.click_io.info(
                            f'INFO: The tag "{image_ref}" is not a unique, commit-specific tag. Deploying the corresponding commit tag "{tag}" instead.'
                        )
                        return tag
        self.click_io.warn(
            f'WARNING: The AWS ECR image "{image_ref}" has no associated commit tag so deploying "{image_ref}". Note this could result in images with unintended or incompatible changes being deployed if new ECS Tasks for your service.'
        )
        return image_ref

    @staticmethod
    def _check_image_details_exists(image_info: dict, image_ref: str):
        """Error handling for any unexpected scenario where AWS ECR returns a
        malformed response."""

        if "imageDetails" not in image_info:
            raise ImageNotFoundException(image_ref)

    def _get_client(self):
        if not self.session:
            self.session = get_aws_session_or_abort()
        return self.session.client("ecr")
