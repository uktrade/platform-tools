import re

import jinja2

from dbt_platform_helper.jinja2_tags import ExtraHeaderTag
from dbt_platform_helper.jinja2_tags import VersionTag

S3_CROSS_ACCOUNT_POLICY = "addons/svc/s3-cross-account-policy.yml"

ADDON_TEMPLATE_MAP = {
    "s3": ["addons/svc/s3-policy.yml"],
    "s3-policy": ["addons/svc/s3-policy.yml"],
    "appconfig-ipfilter": ["addons/svc/appconfig-ipfilter.yml"],
    "subscription-filter": ["addons/svc/subscription-filter.yml"],
    "prometheus-policy": ["addons/svc/prometheus-policy.yml"],
}


def camel_case(s):
    s = re.sub(r"(_|-)+", " ", s).title().replace(" ", "")
    return "".join([s[0].lower(), s[1:]])


def setup_templates() -> jinja2.Environment:
    templateLoader = jinja2.PackageLoader("dbt_platform_helper")
    templateEnv = jinja2.Environment(loader=templateLoader, keep_trailing_newline=True)
    templateEnv.add_extension(ExtraHeaderTag)
    templateEnv.add_extension(VersionTag)

    return templateEnv
