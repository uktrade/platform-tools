from dbt_platform_helper.providers.io import ClickIOProvider


class ECRHousekeeping:
    def __init__(self, image_provider, live_image_providers, io=None):
        self.image_provider = image_provider
        self.live_image_providers = live_image_providers
        self.io = io or ClickIOProvider()

    def tag_stale_images_for_deletion(
        self,
    ):
        live_images = []

        for provider in self.live_image_providers:
            images = provider.get_live_images()
            self.io.info(f"{len(images)} live images in {provider.session.profile_name}")
            live_images += images

        unique_live_images = list(set(live_images))

        self.io.info(f"Found {len(unique_live_images)} unique live images")

        old_images = self.image_provider.get_old_images()
        self.io.info(f"Found {len(old_images)} old images")

        in_use_image_shas = [
            self.image_provider.get_image_shas(image) for image in unique_live_images
        ]

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
