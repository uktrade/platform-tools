class ImageProvider:
    def __init__(self, session):
        self.session = session


class ECRHousekeeping:
    def __init__(self, image_provider):
        self.image_provider = image_provider

    def tag_stale_images_for_deletion(
        self,
    ):
        return "Tagged x/y images for deletion"
