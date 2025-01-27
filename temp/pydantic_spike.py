import json
from typing import Dict

import jsonref
import yaml
from pydantic import BaseModel
from pydantic import Field
from pydantic import RootModel


class InnerDict(BaseModel):
    property_1: str
    property_2: str


class DictOfDictsOnlySpecificNamesAllowed(BaseModel):
    specific_name_1: InnerDict
    specific_name_2: InnerDict


class DictOfDictsAnyNameAllowed(RootModel[Dict[str, Dict]]):
    root: Dict[str, InnerDict] = Field(description="Any number of InnerDicts with any key")


class PlatformConfig(BaseModel):
    application: str = Field(
        description="The name of your application. Letters, numbers, hyphens and underscores are allowed."
    )
    dict_of_dicts_only_specific_names_allowed: DictOfDictsOnlySpecificNamesAllowed
    dict_of_dicts_any_name_allowed: DictOfDictsAnyNameAllowed


without_refs = jsonref.replace_refs(PlatformConfig.model_json_schema(), proxies=False)

del without_refs["$defs"]

print("SCHEMA SPECIFICATION...")
print(json.dumps(without_refs, indent=4))

print("VALIDATE SOME CONFIG...")
with open("temp/platform_config.yml") as config_file:
    platform_config = yaml.safe_load(config_file)
    print(json.dumps(platform_config, indent=4))

try:
    PlatformConfig.model_validate(platform_config)
    print("Validation succeeded")
except Exception as error:
    print("Validation failed")
    print(str(error))
