import json

import yaml
from schema import Literal
from schema import Schema

schema = Schema(
    {
        Literal(
            "application",
            description="The name of your application. Letters, numbers, hyphens and underscores are allowed.",
        ): str,
        "dict_of_dicts_only_specific_names_allowed": {
            "specific_name_1": {"property_1": str, "property_2": str},
            "specific_name_2": {"property_1": str, "property_2": str},
        },
        "dict_of_dicts_any_name_allowed": {str: {"property_1": str, "property_2": str}},
    }
)

print("SCHEMA SPECIFICATION...")
print(json.dumps(schema.json_schema("does-not-matter"), indent=4))

print("VALIDATE SOME CONFIG...")
with open("temp/platform_config.yml") as config_file:
    platform_config = yaml.safe_load(config_file)
    print(json.dumps(platform_config, indent=4))

try:
    schema.validate(platform_config)
    print("Validation succeeded")
except Exception as error:
    print("Validation failed")
    print(str(error))
