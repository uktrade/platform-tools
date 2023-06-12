from pathlib import Path

import jsonschema
import pytest
import yaml

BASE_DIR = Path(__file__).parent.parent


# tell yaml to ignore CFN ! function prefixes
yaml.add_multi_constructor("!", lambda loader, suffix, node: None, Loader=yaml.SafeLoader)


@pytest.fixture
def fakefs(fs):
    """Mock file system fixture with the templates and schemas dirs retained"""
    fs.add_real_directory(BASE_DIR / "templates")
    fs.add_real_directory(BASE_DIR / "schemas")
    fs.add_real_file(BASE_DIR / "storage-plans.yml")
    fs.add_real_file(BASE_DIR / "default-storage.yml")
    fs.add_real_directory(Path(jsonschema.__path__[0]) / "schemas/vocabularies")

    return fs
