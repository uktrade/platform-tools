from dbt_platform_helper.providers.io import ClickIOProvider


def abort_with_error(message):
    ClickIOProvider().abort_with_error(message)
