import re

import jinja2

from dbt_platform_helper.jinja2_tags import ExtraHeaderTag
from dbt_platform_helper.jinja2_tags import VersionTag


def camel_case(s):
    s = re.sub(r"(_|-)+", " ", s).title().replace(" ", "")
    return "".join([s[0].lower(), s[1:]])


def setup_templates() -> jinja2.Environment:
    templateLoader = jinja2.PackageLoader("dbt_platform_helper")
    templateEnv = jinja2.Environment(loader=templateLoader, keep_trailing_newline=True)
    templateEnv.add_extension(ExtraHeaderTag)
    templateEnv.add_extension(VersionTag)

    return templateEnv
