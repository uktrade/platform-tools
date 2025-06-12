import click

from dbt_platform_helper.domain.ecr_housekeeping import ECRHousekeeping
from dbt_platform_helper.domain.ecr_housekeeping import ImageProvider
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.in_use_image_provider import InUseImageProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.click import ClickDocOptGroup


@click.group(cls=ClickDocOptGroup, help="Housekeeping tasks for ECR image cleanup.")
def ecr_housekeeping():
    PlatformHelperVersioning().check_if_needs_update()


@ecr_housekeeping.command(
    help="Adds a pending-deletion image tag to any stale unused images in the ECR repository",
)
def tag_stale_images_for_deletion():
    try:
        io = ClickIOProvider()
        session = get_aws_session_or_abort()
        image_provider = ImageProvider(session)
        in_use_image_provider = InUseImageProvider(session)
        result = ECRHousekeeping(
            image_provider, in_use_image_provider
        ).tag_stale_images_for_deletion()

        io.info(result)

    except PlatformException as err:
        io.abort_with_error(str(err))
