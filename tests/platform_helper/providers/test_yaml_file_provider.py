from pathlib import Path

import pytest

from dbt_platform_helper.providers.yaml_file import DuplicateKeysException
from dbt_platform_helper.providers.yaml_file import FileNotFoundException
from dbt_platform_helper.providers.yaml_file import InvalidYamlException
from dbt_platform_helper.providers.yaml_file import YamlFileProvider


def test_returns_valid_yaml(fs):
    test_path = "./test"
    fs.create_file(Path(test_path), contents="key: value")
    result = YamlFileProvider.load(test_path)
    assert result == {"key": "value"}


def test_returns_empty_dict_given_empty_yaml(fs):
    test_path = "./test"
    fs.create_file(Path(test_path), contents="")
    result = YamlFileProvider.load(test_path)
    assert result == {}


def test_raises_exception_if_invalid_yaml(fs):
    test_path = "./test"
    fs.create_file(Path(test_path), contents="{")
    with pytest.raises(InvalidYamlException):
        YamlFileProvider.load(test_path)


def test_raises_exception_if_duplicate_keys_in_yaml(fs):
    test_path = "./test"
    fs.create_file(Path(test_path), contents="key1: name\nkey2: name\nkey1: name")
    with pytest.raises(DuplicateKeysException):
        YamlFileProvider.load(test_path)


def test_raises_exception_if_path_doesnt_exist(fs):
    test_path = "./test"
    with pytest.raises(FileNotFoundException):
        YamlFileProvider.load(test_path)


def test_writes_with_correct_contents(fs):
    test_path = ".platform-helper-config-cache.yml"
    test_content = {
        "redis": {"date-retrieved": "09-02-02 10:35:48", "versions": ["7.1", "7.2"]},
        "opensearch": {"date-retrieved": "09-12-24 16:00:00", "versions": ["6.1", "6.2"]},
    }
    test_comment = "# [!] This file is autogenerated via the platform-helper. Do not edit.\n"
    expected_test_cache_file = """# [!] This file is autogenerated via the platform-helper. Do not edit.
redis:
  date-retrieved: 09-02-02 10:35:48
  versions:
  - '7.1'
  - '7.2'
opensearch:
  date-retrieved: 09-12-24 16:00:00
  versions:
  - '6.1'
  - '6.2'
"""

    YamlFileProvider.write(test_path, test_content, test_comment)
    with open(test_path, "r") as test_yaml_file:
        assert expected_test_cache_file in test_yaml_file.read()


def test_writes_with_no_comment(fs):
    test_path = "./test"
    test_content = {
        "redis": {"date-retrieved": "09-02-02 10:35:48", "versions": ["7.1", "7.2"]},
        "opensearch": {"date-retrieved": "09-12-24 16:00:00", "versions": ["6.1", "6.2"]},
    }
    expected_test_cache_file = """redis:
  date-retrieved: 09-02-02 10:35:48
  versions:
  - '7.1'
  - '7.2'
opensearch:
  date-retrieved: 09-12-24 16:00:00
  versions:
  - '6.1'
  - '6.2'
"""

    YamlFileProvider.write(test_path, test_content)
    with open(test_path, "r") as test_yaml_file:
        assert expected_test_cache_file in test_yaml_file.read()
