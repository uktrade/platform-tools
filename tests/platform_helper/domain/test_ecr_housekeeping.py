from unittest.mock import create_autospec

from dbt_platform_helper.domain.ecr_housekeeping import ECRHousekeeping
from dbt_platform_helper.domain.ecr_housekeeping import ImageProvider


class TestECRHousekeeping:
    def tag_stale_images_for_deletion(
        self,
    ):
        mock_image_provider = create_autospec(ImageProvider, spec_set=True)

        result = ECRHousekeeping(mock_image_provider).tag_stale_images_for_deletion()

        assert result == "Tagged x/y images for deletion"
