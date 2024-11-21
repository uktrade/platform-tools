from pathlib import Path

from dbt_platform_helper.utils.manifests import get_repository_name_from_manifest
from dbt_platform_helper.utils.manifests import get_service_name_from_manifest
from tests.platform_helper.conftest import UTILS_FIXTURES_DIR


def test_get_service_name_from_manifest():
    service_manifest = Path(UTILS_FIXTURES_DIR / "test_service_manifest.yml")

    name = get_service_name_from_manifest(service_manifest)

    assert name == "test-public-service"


def test_get_repository_name_from_manifest():
    service_manifest = Path(UTILS_FIXTURES_DIR / "test_service_manifest.yml")

    repository = get_repository_name_from_manifest(service_manifest)

    assert repository == "testapp/test-public-service"
