from pathlib import Path

import pytest

from dbt_platform_helper.providers.yaml_file_provider import DuplicateKeysException
from dbt_platform_helper.providers.yaml_file_provider import InvalidYamlException
from dbt_platform_helper.providers.yaml_file_provider import YamlFileProvider


def test_returns_valid_yaml(fs):
    test_path = "./test_success_path"
    fs.create_file(Path(test_path), contents="key: value")
    result = YamlFileProvider.load(test_path)
    assert result == {"key": "value"}


def test_returns_empty_dict_given_empty_yaml(fs):
    test_path = "./test_empty_yaml_path"
    fs.create_file(Path(test_path), contents="")
    result = YamlFileProvider.load(test_path)
    assert result == {}


def test_raises_exception_if_invalid_yaml(fs):
    test_path = "./test_invalid_path"
    fs.create_file(Path(test_path), contents="{")
    with pytest.raises(InvalidYamlException):
        YamlFileProvider.load(test_path)


def test_raises_exception_if_duplicate_keys_in_yaml(fs):
    test_path = "./test_duplicate_keys_path"
    fs.create_file(Path(test_path), contents="key1: name\nkey2: name\nkey1: name")
    with pytest.raises(DuplicateKeysException):
        YamlFileProvider.load(test_path)
