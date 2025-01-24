from pathlib import Path

import yaml
from yaml.parser import ParserError
from yamllint import linter
from yamllint.config import YamlLintConfig


class FileProviderException(Exception):
    pass


class YamlFileProviderException(FileProviderException):
    pass


class FileNotFoundException(FileProviderException):
    pass


class InvalidYamlException(YamlFileProviderException):
    pass


class DuplicateKeysException(YamlFileProviderException):
    pass


class YamlFileProvider:
    def load(path: str) -> dict:
        """
        Raises:
            FileNotFoundException: file is not there
            InvalidYamlException: file contains invalid yaml
            DuplicateKeysException: yaml contains duplicate keys
        """
        if not Path(path).exists():
            raise FileNotFoundException(f"`{path}` is missing.")
        try:
            yaml_content = yaml.safe_load(Path(path).read_text())
        except ParserError:
            raise InvalidYamlException(f"{path} is not valid YAML.")

        if not yaml_content:
            return {}

        YamlFileProvider.lint_yaml_for_duplicate_keys(path)

        return yaml_content

    def write(path: str, contents: dict, comment: str = ""):
        with open(path, "w") as file:
            file.write(comment)
            yaml.dump(contents, file)

    @staticmethod
    def lint_yaml_for_duplicate_keys(path):
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
