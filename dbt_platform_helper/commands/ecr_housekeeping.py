import click

from dbt_platform_helper.domain.ecr_housekeeping import ECRHousekeeping
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.ecr_image_provider import ECRImageProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.live_image_provider import LiveImageProvider
from dbt_platform_helper.utils.aws import get_aws_session_or_abort
from dbt_platform_helper.utils.click import ClickDocOptGroup


@click.group(cls=ClickDocOptGroup, help="Housekeeping tasks for ECR image cleanup.")
def ecr_housekeeping():
    PlatformHelperVersioning().check_if_needs_update()


@ecr_housekeeping.command(
    help="Adds a pending-deletion image tag to any stale unused images in the ECR repository",
)
@click.argument("prod_profile", type=str, required=True)
def tag_stale_images_for_deletion(prod_profile: str):
    try:
        io = ClickIOProvider()
        session = get_aws_session_or_abort()  # Need to get all relevant sessions
        prod_session = get_aws_session_or_abort(prod_profile)  # Need to get all relevant sessions
        image_provider = ECRImageProvider(session)
        live_image_providers = [LiveImageProvider(session), LiveImageProvider(prod_session)]
        result = ECRHousekeeping(
            image_provider, live_image_providers
        ).tag_stale_images_for_deletion()

        io.info(result)

    except PlatformException as err:
        io.abort_with_error(str(err))


# @ecr_housekeeping.command(
#     help="Adds a pending-deletion image tag to any stale unused images in the ECR repository",
# )
# def list_tagged_for_deletion():
#     try:
#         io = ClickIOProvider()
#         session = get_aws_session_or_abort()
#         result = ECRImageProvider(session).list_tagged_for_deletion()
#         for image in result:
#             io.info(f"{image["sha"]}, {image["pushed_at"]}")

#     except PlatformException as err:
#         io.abort_with_error(str(err))


@ecr_housekeeping.command(
    help="Lists in-use images from current EC2 tasks",
)
def list_live_images():
    try:
        io = ClickIOProvider()
        session = get_aws_session_or_abort()
        result = LiveImageProvider(session).get_live_images()

        io.info(f"Found {len(result)} images that are live in ECS tasks definitions:\n")

        for image in result:
            io.info(image)

    except PlatformException as err:
        io.abort_with_error(str(err))
