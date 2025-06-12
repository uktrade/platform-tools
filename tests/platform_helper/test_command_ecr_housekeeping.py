from unittest.mock import Mock
from unittest.mock import create_autospec
from unittest.mock import patch

from boto3 import Session
from click.testing import CliRunner

from dbt_platform_helper.commands.ecr_housekeeping import (
    tag_stale_images_for_deletion as tag_stale_images_for_deletion_command,
)
from dbt_platform_helper.domain.ecr_housekeeping import ECRHousekeeping
from dbt_platform_helper.domain.ecr_housekeeping import ImageProvider
from dbt_platform_helper.providers.io import ClickIOProvider


class TestECRHousekeeping:
    @patch("dbt_platform_helper.commands.ecr_housekeeping.get_aws_session_or_abort")
    @patch("dbt_platform_helper.commands.ecr_housekeeping.ClickIOProvider")
    @patch("dbt_platform_helper.commands.ecr_housekeeping.ImageProvider")
    @patch("dbt_platform_helper.commands.ecr_housekeeping.ECRHousekeeping")
    def test_success_when_calling_tag_stale_images_for_deletion(
        self,
        mock_domain,
        mock_provider,
        mock_io,
        mock_session,
    ):
        mock_io_instance = Mock(spec=ClickIOProvider)
        mock_io.return_value = mock_io_instance
        mock_session_instance = Mock(spec=Session)
        mock_session.return_value = mock_session_instance
        mock_domain_instance = create_autospec(ECRHousekeeping, spec_set=True)
        mock_domain.return_value = mock_domain_instance
        mock_provider_instance = create_autospec(ImageProvider, spec_set=True)
        mock_provider.return_value = mock_provider_instance
        mock_domain_instance.tag_stale_images_for_deletion.return_value = (
            "Tagged x/y images for deletion"
        )

        result = CliRunner().invoke(tag_stale_images_for_deletion_command)

        assert result.exit_code == 0

        mock_provider.assert_called_once_with(mock_session_instance)
        mock_domain.assert_called_once_with(mock_provider_instance)

        mock_domain_instance.tag_stale_images_for_deletion.assert_called_once()
        mock_io_instance.info.assert_called_once_with("Tagged x/y images for deletion")
