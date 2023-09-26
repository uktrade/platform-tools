import re

from schema import SchemaError


def validate_string(regex_pattern):
    def validator(string):
        if not re.match(regex_pattern, string):
            raise SchemaError(
                f"String '{string}' does not match the required pattern '{regex_pattern}'. For more details on valid string patterns see: https://aws.github.io/copilot-cli/docs/manifest/lb-web-service/"
            )
        return string

    return validator
