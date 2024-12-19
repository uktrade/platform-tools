from pathlib import Path

import yaml
from yaml.parser import ParserError
from yamllint import linter
from yamllint.config import YamlLintConfig


class YamlFileProviderException(Exception):
    pass


class InvalidYamlException(YamlFileProviderException):
    pass


class DuplicateKeysException(YamlFileProviderException):
    pass


class FileNotFoundException(YamlFileProviderException):
    pass


class YamlFileProvider:
    def load(path):
        if not Path(path).exists():
            raise FileNotFoundException
        try:
            yaml_content = yaml.safe_load(Path(path).read_text())
        except ParserError:
            raise InvalidYamlException

        if not yaml_content:
            return {}

        YamlFileProvider._lint_yaml_for_duplicate_keys(path)

        return yaml_content

    def _lint_yaml_for_duplicate_keys(path):
        duplicate_keys = []
        with open(path, "r") as yaml_file:
            file_contents = yaml_file.read()
            results = linter.run(
                file_contents, YamlLintConfig(yaml.dump({"rules": {"key-duplicates": "enable"}}))
            )
            duplicate_keys = [
                "\t"
                + f"Line {result.line}: {result.message}".replace(
                    " in mapping (key-duplicates)", ""
                )
                for result in results
            ]
        if duplicate_keys:
            raise DuplicateKeysException(",".join(duplicate_keys))
