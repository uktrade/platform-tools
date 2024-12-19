from pathlib import Path

import pytest
import yaml
from yaml.parser import ParserError
from yamllint import linter
from yamllint.config import YamlLintConfig


class YamlFileProvider:
    def load(path):
        try:
            yaml_content = yaml.safe_load(Path(path).read_text())
        except ParserError:
            raise InvalidYamlException

        if yaml_content:
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


class YamlFileProviderException(Exception):
    pass


class InvalidYamlException(YamlFileProviderException):
    pass


class DuplicateKeysException(YamlFileProviderException):
    pass


class TestYamlFileProvider:
    def test_returns_valid_yaml(fs):
        test_path = "./test_path"
        Path(test_path).write_text("key: value")
        result = YamlFileProvider.load(test_path)
        assert result == {"key": "value"}

    def test_raises_exception_if_invalid_yaml(fs):
        test_path = "./test_invalid_path"
        Path(test_path).write_text("{")
        with pytest.raises(InvalidYamlException):
            YamlFileProvider.load(test_path)

    def test_raises_exception_if_duplicate_keys_in_yaml(fs):
        test_path = "./test_duplicate_keys_path"
        Path(test_path).write_text("key1: name\nkey2: name\nkey1: name")
        with pytest.raises(DuplicateKeysException):
            YamlFileProvider.load(test_path)
