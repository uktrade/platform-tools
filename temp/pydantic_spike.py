import json
from typing import Dict

import jsonref
import yaml
from pydantic import BaseModel
from pydantic import Field
from pydantic import RootModel


class InnerDict(BaseModel):
    property_1: str = Field(description="Must be a string")
    property_2: str = Field(description="Must be a string")


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

# Expected output...
#
# ➜ python temp/pydantic_spike.py
# SCHEMA SPECIFICATION...
# {
#     "properties": {
#         "application": {
#             "description": "The name of your application. Letters, numbers, hyphens and underscores are allowed.",
#             "title": "Application",
#             "type": "string"
#         },
#         "dict_of_dicts_only_specific_names_allowed": {
#             "properties": {
#                 "specific_name_1": {
#                     "properties": {
#                         "property_1": {
#                             "description": "Must be a string",
#                             "title": "Property 1",
#                             "type": "string"
#                         },
#                         "property_2": {
#                             "description": "Must be a string",
#                             "title": "Property 2",
#                             "type": "string"
#                         }
#                     },
#                     "required": [
#                         "property_1",
#                         "property_2"
#                     ],
#                     "title": "InnerDict",
#                     "type": "object"
#                 },
#                 "specific_name_2": {
#                     "properties": {
#                         "property_1": {
#                             "description": "Must be a string",
#                             "title": "Property 1",
#                             "type": "string"
#                         },
#                         "property_2": {
#                             "description": "Must be a string",
#                             "title": "Property 2",
#                             "type": "string"
#                         }
#                     },
#                     "required": [
#                         "property_1",
#                         "property_2"
#                     ],
#                     "title": "InnerDict",
#                     "type": "object"
#                 }
#             },
#             "required": [
#                 "specific_name_1",
#                 "specific_name_2"
#             ],
#             "title": "DictOfDictsOnlySpecificNamesAllowed",
#             "type": "object"
#         },
#         "dict_of_dicts_any_name_allowed": {
#             "additionalProperties": {
#                 "properties": {
#                     "property_1": {
#                         "description": "Must be a string",
#                         "title": "Property 1",
#                         "type": "string"
#                     },
#                     "property_2": {
#                         "description": "Must be a string",
#                         "title": "Property 2",
#                         "type": "string"
#                     }
#                 },
#                 "required": [
#                     "property_1",
#                     "property_2"
#                 ],
#                 "title": "InnerDict",
#                 "type": "object"
#             },
#             "description": "Any number of InnerDicts with any key",
#             "title": "DictOfDictsAnyNameAllowed",
#             "type": "object"
#         }
#     },
#     "required": [
#         "application",
#         "dict_of_dicts_only_specific_names_allowed",
#         "dict_of_dicts_any_name_allowed"
#     ],
#     "title": "PlatformConfig",
#     "type": "object"
# }
# VALIDATE SOME CONFIG...
# {
#     "application": "test-application",
#     "dict_of_dicts_only_specific_names_allowed": {
#         "specific_name_1": {
#             "property_1": "specific-name-1-property-1",
#             "property_2": "specific-name-1-property-2"
#         },
#         "specific_name_2": {
#             "property_1": "specific-name-2-property-1",
#             "property_2": "specific-name-2-property-2"
#         }
#     },
#     "dict_of_dicts_any_name_allowed": {
#         "any_name_1": {
#             "property_1": "any-name-1-property-1",
#             "property_2": "any-name-1-property-2"
#         },
#         "any_name_2": {
#             "property_1": "any-name-2-property-1",
#             "property_2": "any-name-2-property-2"
#         }
#     }
# }
# Validation succeeded
