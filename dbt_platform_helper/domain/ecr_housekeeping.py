class ImageProvider:
    def __init__(self, session):
        self.session = session
        self.private_ecr_client = session.client("ecr")
        self.public_ecr_client = session.client("ecr-public", region_name="us-east-1")
        self.sts_client = session.client("sts")
        self.ecs_client = session.client("ecs")


class ECRHousekeeping:
    def __init__(self, image_provider):
        self.image_provider = image_provider

    def tag_stale_images_for_deletion(
        self,
    ):
        return "Tagged x/y images for deletion"
