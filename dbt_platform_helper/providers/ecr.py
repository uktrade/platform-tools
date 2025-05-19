from collections import defaultdict

import botocore
from boto3 import Session

from dbt_platform_helper.providers.aws.exceptions import AWSException
from dbt_platform_helper.providers.aws.exceptions import ImageNotFoundException
from dbt_platform_helper.providers.aws.exceptions import MultipleImagesFoundException
from dbt_platform_helper.providers.aws.exceptions import RepositoryNotFoundException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.utils.aws import get_aws_session_or_abort

NOT_A_UNIQUE_TAG_INFO = 'INFO: The tag "{image_ref}" is not a unique, commit-specific tag. Deploying the corresponding commit tag "{commit_tag}" instead.'
NO_ASSOCIATED_COMMIT_TAG_WARNING = 'WARNING: The AWS ECR image "{image_ref}" has no associated commit tag so deploying "{image_ref}". Note this could result in images with unintended or incompatible changes being deployed in new ECS Tasks for your service.'


class ECRProvider:
    def __init__(self, session: Session = None, click_io: ClickIOProvider = ClickIOProvider()):
        self.session = session
        self.click_io = click_io

    def get_ecr_repo_names(self) -> list[str]:
        out = []
        for page in self._get_client().get_paginator("describe_repositories").paginate():
            out.extend([repo["repositoryName"] for repo in page.get("repositories", {})])
        return out

    def get_commit_tag_for_reference(self, application_name: str, codebase: str, image_ref: str):
        repository = f"{application_name}/{codebase}"
        next_page_token = None
        tag_map = {}
        digest_map = defaultdict(dict)

        while True:
            image_list = self._get_ecr_images(repository, image_ref, next_page_token)
            next_page_token = image_list.get("nextToken")

            for image in image_list["imageIds"]:
                digest, tag = image["imageDigest"], image["imageTag"]
                digest_map[digest][tag.split("-")[0]] = tag
                tag_map[tag] = digest

            if not next_page_token:
                break

        if image_ref.startswith("commit-"):
            if image_ref in tag_map:
                return image_ref
            else:
                candidates = [
                    tag
                    for tag in tag_map.keys()
                    if image_ref.startswith(tag) or tag.startswith(image_ref)
                ]
                if not candidates:
                    raise ImageNotFoundException(image_ref)
                if len(candidates) > 1:
                    raise MultipleImagesFoundException(image_ref, candidates)
                return candidates[0]
        else:
            digest = tag_map.get(image_ref)
            if not digest:
                raise ImageNotFoundException(image_ref)

            commit_tag = digest_map.get(digest, dict()).get("commit")

            if commit_tag:
                self.click_io.info(
                    NOT_A_UNIQUE_TAG_INFO.format(image_ref=image_ref, commit_tag=commit_tag)
                )
                return commit_tag
            else:
                self.click_io.warn(NO_ASSOCIATED_COMMIT_TAG_WARNING.format(image_ref=image_ref))
                return image_ref

    def _get_ecr_images(self, repository, image_ref, next_page_token):
        params = {"repositoryName": repository, "filter": {"tagStatus": "TAGGED"}}
        if next_page_token:
            params["nextToken"] = next_page_token
        try:
            image_list = self._get_client().list_images(**params)
            return image_list
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "RepositoryNotFoundException":
                raise RepositoryNotFoundException(repository)
            else:
                raise AWSException(
                    f"Unexpected error for repo '{repository}' and image reference '{image_ref}': {e}"
                )

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
