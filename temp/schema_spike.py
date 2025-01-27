import json

import yaml
from schema import Literal
from schema import Schema

inner_dict = {
    Literal("property_1", description="Must be a string"): str,
    Literal("property_2", description="Must be a string"): str,
}
schema = Schema(
    {
        Literal(
            "application",
            description="The name of your application. Letters, numbers, hyphens and underscores are allowed.",
        ): str,
        "dict_of_dicts_only_specific_names_allowed": {
            "specific_name_1": inner_dict,
            "specific_name_2": inner_dict,
        },
        Literal(
            "dict_of_dicts_any_name_allowed", description="Any number of InnerDicts with any key"
        ): {str: inner_dict},
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

# Expected output...
#
# ➜ python temp/schema_spike.py
# SCHEMA SPECIFICATION...
# {
#     "type": "object",
#     "properties": {
#         "application": {
#             "description": "The name of your application. Letters, numbers, hyphens and underscores are allowed.",
#             "type": "string"
#         },
#         "dict_of_dicts_only_specific_names_allowed": {
#             "type": "object",
#             "properties": {
#                 "specific_name_1": {
#                     "type": "object",
#                     "properties": {
#                         "property_1": {
#                             "description": "Must be a string",
#                             "type": "string"
#                         },
#                         "property_2": {
#                             "description": "Must be a string",
#                             "type": "string"
#                         }
#                     },
#                     "required": [
#                         "property_1",
#                         "property_2"
#                     ],
#                     "additionalProperties": false
#                 },
#                 "specific_name_2": {
#                     "type": "object",
#                     "properties": {
#                         "property_1": {
#                             "description": "Must be a string",
#                             "type": "string"
#                         },
#                         "property_2": {
#                             "description": "Must be a string",
#                             "type": "string"
#                         }
#                     },
#                     "required": [
#                         "property_1",
#                         "property_2"
#                     ],
#                     "additionalProperties": false
#                 }
#             },
#             "required": [
#                 "specific_name_1",
#                 "specific_name_2"
#             ],
#             "additionalProperties": false
#         },
#         "dict_of_dicts_any_name_allowed": {
#             "description": "Any number of InnerDicts with any key",
#             "type": "object",
#             "properties": {},
#             "required": [],
#             "additionalProperties": true
#         }
#     },
#     "required": [
#         "application",
#         "dict_of_dicts_only_specific_names_allowed",
#         "dict_of_dicts_any_name_allowed"
#     ],
#     "additionalProperties": false,
#     "$id": "does-not-matter",
#     "$schema": "http://json-schema.org/draft-07/schema#"
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
