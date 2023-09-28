import re
from pathlib import Path

import jinja2

from dbt_copilot_helper.jinja2_tags import VersionTag


def camel_case(s):
    s = re.sub(r"(_|-)+", " ", s).title().replace(" ", "")
    return "".join([s[0].lower(), s[1:]])


def setup_templates() -> jinja2.Environment:
    Path(__file__).parent.parent / Path("templates")
    templateLoader = jinja2.PackageLoader("dbt_copilot_helper")
    templateEnv = jinja2.Environment(loader=templateLoader, keep_trailing_newline=True)
    templateEnv.add_extension(VersionTag)

    return templateEnv
