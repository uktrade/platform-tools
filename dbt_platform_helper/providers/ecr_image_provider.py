from datetime import datetime
from datetime import timezone

from botocore.exceptions import ClientError

from dbt_platform_helper.providers.io import ClickIOProvider


class ECRImageProvider:

    EXPIRATION_DAYS = 90

    def __init__(self, session, io=None):
        self.session = session
        self.private_ecr_client = session.client("ecr")
        self.public_ecr_client = session.client("ecr-public", region_name="us-east-1")
        self.io = io or ClickIOProvider()

    def get_old_images(self):
        return self._get_old_images(self.private_ecr_client) + self._get_old_images(
            self.public_ecr_client
        )

    def all_images_present_in_repositories(self, image_shas):
        private_repos = self._get_ecr_repos(self.private_ecr_client)
        public_repos = self._get_ecr_repos(self.public_ecr_client)
        private_images = []
        public_images = []
        for repo in private_repos:
            private_images += self._get_images_for_repository(
                self.private_ecr_client, repo["repositoryName"]
            )
        for repo in public_repos:
            public_images += self._get_images_for_repository(
                self.public_ecr_client, repo["repositoryName"]
            )
        all_images = public_images + private_images

        all_image_shas = [image["image_digest"] for image in all_images if image["image_digest"]]

        for image in image_shas:
            if image and image not in all_image_shas:
                self.io.info(f"image digest {image} was not found in any of the respositories")
                return False
        return True

    def _get_old_images(self, ecr_client):
        old_images = []
        today = datetime.now(timezone.utc)

        for repository in self._get_ecr_repos(ecr_client):
            images = self._get_images_for_repository(
                ecr_client, repository=repository["repositoryName"]
            )

            for image in images:
                image_push_days = (today - image["push_date"].astimezone(timezone.utc)).days

                if image_push_days > ECRImageProvider.EXPIRATION_DAYS:
                    old_images.append(image["image_digest"])

        return old_images

    def _get_ecr_repos(self, ecr_client) -> list:
        repositories = []
        paginator = ecr_client.get_paginator("describe_repositories")
        page_iterator = paginator.paginate()
        for page in page_iterator:
            repositories.extend(page["repositories"])

        return repositories

    def _get_images_for_repository(self, ecr_client, repository: str) -> list:

        images = []

        paginator = ecr_client.get_paginator("describe_images")
        page_iterator = paginator.paginate(repositoryName=repository)
        for page in page_iterator:
            for image in page["imageDetails"]:
                images.append(
                    {
                        "push_date": image["imagePushedAt"],
                        "image_digest": image["imageDigest"],
                    }
                )

        return images

    def _is_private_repository_image(self, image):
        return "public" in image and "uktrade" in image

    def get_image_shas(self, image):
        if self._is_private_repository_image(image):
            try:
                repository_name = "/".join(image.split("/")[2:]).split(":")[0]
                response = self.public_ecr_client.describe_images(
                    repositoryName=repository_name,
                    imageIds=[{"imageTag": image.split(":")[1]}],
                )

                return response["imageDetails"][0]["imageDigest"]

            except ClientError as ce:
                if ce.response["Error"]["Code"] == "RepositoryNotFoundException":
                    self.io.debug(f"Repository {repository_name} not found")
                    return
        else:
            try:
                repository_name = image.split("/", 1)[1].split(":")[0]
                response = self.private_ecr_client.batch_get_image(
                    repositoryName=repository_name,
                    imageIds=[{"imageTag": image.split(":")[1]}],
                )

                return response["images"][0]["imageId"]["imageDigest"]
            except ClientError as ce:
                if ce.response["Error"]["Code"] == "RepositoryNotFoundException":
                    self.io.debug(f"Repository {repository_name} not found")
                    return
