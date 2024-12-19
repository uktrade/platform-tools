from pathlib import Path

import yaml


class YamlFileProvider:
    def get_yaml(path):
        return yaml.safe_load(Path(path).read_text())


class TestYamlFileProvider:
    def test_returns_valid_yaml(fakefs):
        test_path = "./test_path"
        Path("./test_path").write_text("key: value")
        result = YamlFileProvider.get_yaml(test_path)
        assert result == {"key": "value"}
