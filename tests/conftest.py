from pathlib import Path

import pytest


@pytest.fixture
def fakefs(fs):
    """Mock file system fixure with the templates and schemas dirs retained."""
    fs.add_real_directory(Path(__file__).parent.parent / "templates")
    fs.add_real_directory(Path(__file__).parent.parent / "schemas")

    return fs
