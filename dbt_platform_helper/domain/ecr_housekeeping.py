class ECRHousekeeping:
    def __init__(self, image_provider, live_image_provider):
        self.image_provider = image_provider
        self.live_image_provider = live_image_provider

    def tag_stale_images_for_deletion(
        self,
    ):
        live_images = self.live_image_provider.get_in_use_images()
        expired_images = self.image_provider.get_expired_images()

        in_use_image_shas = [
            self.image_provider.get_digest_for_image(image) for image in live_images
        ]

        for_deletion = [image for image in expired_images if image not in in_use_image_shas]

        print("Expired images: ", expired_images)
        print("In use images: ", live_images)
        print("For deletion:", for_deletion)

        return "Tagged x/y images for deletion"

    def _get_in_use_image_shas(self):

        in_use_image_shas = []

        for image in self.get_in_use_images():
            digest = self.image_provider.get_digest_for_image(image)
            in_use_image_shas.append(digest)

        return in_use_image_shas

    def get_in_use_images(self):
        self.live_image_provider.get_in_use_images()

    #         if "public" in image and "uktrade" in image:

    # def get_digest_for_image(self):
    #     pass
