from datetime import datetime
from datetime import timezone


class InUseImageProvider:
    EXPIRATION_DAYS = 90
    MINIMUM_REVISION_AGE_DAYS = 7
    TODAY = datetime.now(timezone.utc)

    def __init__(self, session):
        self.session = session
        self.ecs_client = session.client("ecs")

    def get_in_use_images(self) -> list:
        """
        Iterate over each task definition family in the account and build a list
        of all containers defined within any supported task definition revision.

        Returns a list of supported images, with duplicates removed.
        """

        supported_images = []

        for family in _get_active_task_definition_families(self.ecs_client):

            supported_images.extend(
                self._get_supported_images_for_family(task_definition_family=family)
            )

        # Convert the list to a set and back to a list to remove duplicate images.
        # This greatly reduces time needed to check which images are considered in use. e.g. in platform-sandbox it takes the total number of images to check from 421 -> 26
        return list(set(supported_images))

    def _get_supported_images_for_family(self, task_definition_family: str) -> list:
        """
        Returns a list of all supported images from a given task definition
        family.

        A supported image is one that is defined within a supported task
        definition revision.

        A supported task definition revision is defined as being either newer
        than 7 days, or if there is <= 3 task definition revisions that are
        newer than 7 days for a given family, the 3 latest revisions of that
        family.
        """

        paginator = self.ecs_client.get_paginator("list_task_definitions")

        # Get a list of all task definition revisions for a given family
        task_definition_revisions = paginator.paginate(
            familyPrefix=task_definition_family, sort="DESC"
        ).build_full_result()["taskDefinitionArns"]

        three_newest_revisions = task_definition_revisions[:3]
        older_revisions = task_definition_revisions[3:]

        protected_task_definition_data = [
            self.ecs_client.describe_task_definition(taskDefinition=revision)["taskDefinition"]
            for revision in three_newest_revisions
        ]

        for revision in older_revisions:
            response = self.ecs_client.describe_task_definition(taskDefinition=revision)
            age_of_revision = (self.TODAY - response["taskDefinition"]["registeredAt"]).days
            if age_of_revision <= self.MINIMUM_REVISION_AGE_DAYS:
                protected_task_definition_data.append(response["taskDefinition"])
            else:
                break

        protected_images = []

        for revision in protected_task_definition_data:
            for container_definition in revision["containerDefinitions"]:
                protected_images.append(container_definition["image"])

        return protected_images

    def _get_active_task_definition_families(self) -> list:
        """Gets all active task definition families from ECS."""

        task_definition_families = []
        paginator = self.ecs_client.get_paginator("list_task_definition_families")
        page_iterator = paginator.paginate(status="ACTIVE")

        for page in page_iterator:
            task_definition_families.extend(page["families"])

        return task_definition_families


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

    # def get_in_use_images(self):
    # digest = ""
    #         # TODO - will this always work?
    #         if "public" in image and "uktrade" in image:

    # def get_digest_for_image(self):
    #     pass


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

        for image in self.image_provider.get_in_use_images():
            digest = self.image_provider.get_digest_for_image(image)
            in_use_image_shas.append(digest)

        return in_use_image_shas
