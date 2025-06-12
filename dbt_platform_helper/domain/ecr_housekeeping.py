from datetime import datetime
from datetime import timezone

from botocore.exceptions import ClientError


class ImageProvider:
    EXPIRATION_DAYS = 90

    def __init__(self, session):
        self.session = session
        self.private_ecr_client = session.client("ecr")
        self.public_ecr_client = session.client("ecr-public", region_name="us-east-1")
        self.sts_client = session.client("sts")
        self.ecs_client = session.client("ecs")

    def get_expired_images(self):
        return self._get_expired_images(self.private_ecr_client) + self._get_expired_images(
            self.public_ecr_client
        )

    def _get_expired_images(self, ecr_client):
        expired_images = []
        today = datetime.now(timezone.utc)

        for repository in self._get_ecr_repos(ecr_client):
            images = self._get_images_for_repository(
                ecr_client, repository=repository["repositoryName"]
            )

            for image in images:
                image_push_days = (today - image["push_date"].astimezone(timezone.utc)).days

                if image_push_days > ImageProvider.EXPIRATION_DAYS:
                    expired_images.append(image["image_digest"])

        return expired_images

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

    def _is_private_repository_image(image):
        return "public" in image and "uktrade" in image

    def get_image_shas(self, image):
        if self._is_private_repository_image(image):
            try:
                response = self.ecr_public_client.describe_images(
                    repositoryName="/".join(image.split("/")[2:]).split(":")[0],
                    imageIds=[{"imageTag": image.split(":")[1]}],
                )

                return response["imageDetails"][0]["imageDigest"]

            except ClientError as ce:
                if ce.response["Error"]["Code"] == "RepositoryNotFoundException":
                    return
        else:
            try:
                response = self.ecr_private_client.batch_get_image(
                    repositoryName=image.split("/", 1)[1].split(":")[0],
                    imageIds=[{"imageTag": image.split(":")[1]}],
                )

                return response["images"][0]["imageId"]["imageDigest"]
            except ClientError as ce:
                if ce.response["Error"]["Code"] == "RepositoryNotFoundException":
                    return


class ECRHousekeeping:
    def __init__(self, image_provider, in_use_image_provider):
        self.image_provider = image_provider
        self.in_use_image_provider = in_use_image_provider

    def tag_stale_images_for_deletion(
        self,
    ):
        expired_images = self.image_provider.get_expired_images()
        print("Expired images: ", expired_images)

        return "Tagged x/y images for deletion"

    def _get_in_use_image_shas(self):

        in_use_image_shas = []

        for image in self.get_in_use_images():
            digest = self.image_provider.get_digest_for_image(image)
            in_use_image_shas.append(digest)

        return in_use_image_shas

    def get_in_use_images(self):
        self.in_use_image_provider.get_in_use_images()

    #         if "public" in image and "uktrade" in image:

    # def get_digest_for_image(self):
    #     pass
