import json

from schema import Literal
from schema import Schema

schema = Schema(
    {
        Literal(
            "application",
            description="The name of your application. Letters, numbers, hyphens and underscores are allowed.",
        ): str,
        "dict-of-dicts-only-specific-names-allowed": {
            "specific-name-1": {"property-1": str, "property-2": str},
            "specific-name-2": {"property-1": str, "property-2": str},
        },
        "dict-of-dicts-any-name-allowed": {str: {"property-1": str, "property-2": str}},
    }
)

print(json.dumps(schema.json_schema("does-not-matter"), indent=4))
