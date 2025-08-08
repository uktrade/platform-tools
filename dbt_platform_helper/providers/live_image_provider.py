from datetime import datetime
from datetime import timezone


class LiveImageProvider:
    MINIMUM_REVISION_AGE_DAYS = 7
    TODAY = datetime.now(timezone.utc)

    def __init__(self, session):
        self.session = session
        self.ecs_client = session.client("ecs")

    def get_live_images(self) -> list:
        """
        Iterate over each task definition family in the account and build a list
        of all containers defined within any supported task definition revision.

        Returns a list of supported images, with duplicates removed.
        """

        supported_images = []

        for family in self._get_active_task_definition_families():

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
