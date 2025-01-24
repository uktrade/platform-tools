import json

from pydantic import BaseModel
from pydantic import Field
from pydantic import PositiveInt


class Person(BaseModel):
    name: str = Field(description="descr text")
    age: PositiveInt = 0


print(json.dumps(Person.model_json_schema(), indent=4))

# schema = Schema(
#     {
#         Literal("application", description="The name of your application. Letters, numbers, hyphens and underscores are allowed."): str,
#         "dict-of-dicts-only-specific-names-allowed": {
#             "specific-name-1": {
#                 "property-1": str,
#                 "property-2": str
#             },
#             "specific-name-2": {
#                 "property-1": str,
#                 "property-2": str
#             }
#         },
#         "dict-of-dicts-any-name-allowed": {
#             str: {
#                 "property-1": str,
#                 "property-2": str
#             }
#         },
#     }
# )
