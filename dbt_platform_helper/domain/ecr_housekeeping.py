from dbt_platform_helper.providers.io import ClickIOProvider


class ECRHousekeeping:
    def __init__(self, image_provider, live_image_provider, io=None):
        self.image_provider = image_provider
        self.live_image_provider = live_image_provider
        self.io = io or ClickIOProvider()

    def tag_stale_images_for_deletion(
        self,
    ):
        live_images = self.live_image_provider.get_live_images()
        self.io.info(f"Found {len(live_images)} live images")

        old_images = self.image_provider.get_old_images()
        self.io.info(f"Found {len(old_images)} old images")

        in_use_image_shas = [self.image_provider.get_image_shas(image) for image in live_images]

        for_deletion = [image for image in old_images if image not in in_use_image_shas]
        self.io.info(f"Tagging {len(for_deletion)} images for deletion")

        return "Tagged x/y images for deletion"

    def _get_in_use_image_shas(self):

        in_use_image_shas = []

        for image in self.get_in_use_images():
            digest = self.image_provider.get_digest_for_image(image)
            in_use_image_shas.append(digest)

        return in_use_image_shas

    def get_in_use_images(self):
        self.live_image_provider.get_in_use_images()

    def get_digest_for_image(image):
        pass
