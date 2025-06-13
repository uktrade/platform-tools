from dbt_platform_helper.providers.io import ClickIOProvider


class ECRHousekeeping:
    def __init__(self, image_provider, live_image_providers, io=None):
        self.image_provider = image_provider
        self.live_image_providers = live_image_providers
        self.io = io or ClickIOProvider()

    def _get_all_unique_live_images(self):
        live_images = []

        for provider in self.live_image_providers:
            images = provider.get_live_images()
            self.io.info(f"{len(images)} live images in {provider.session.profile_name}")
            live_images += images

        return list(set(live_images))

    def tag_stale_images_for_deletion(
        self,
    ):
        unique_live_images = self._get_all_unique_live_images()

        self.io.info(f"{len(unique_live_images)} unique live images")

        old_images = self.image_provider.get_old_images()

        self.io.info(
            f"{len(old_images)} images older than {self.image_provider.EXPIRATION_DAYS} days"
        )

        in_use_image_shas = [
            self.image_provider.get_image_shas(image) for image in unique_live_images
        ]

        for_deletion = [image for image in old_images if image not in in_use_image_shas]

        if not self.image_provider.all_images_present_in_repositories(in_use_image_shas):
            self.io.abort_with_error(
                "Live image not found in the scanned ECR repositories. Ensure you are logged in with the correct (non-prod) profile for the account where the repositories are located"
            )

        self.io.info(f"\n{len(for_deletion)} images identified for deletion")

        if self.io.confirm(f"\nTag {len(for_deletion)} images for deletion?"):
            return self.io.info("Tagged x/y images for deletion")
        else:
            return self.io.info("\nSkipping tagging images for deletion.  Complete.")

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
