import os

import pytest
import yaml

from dbt_platform_helper.domain.service import ServiceManager


@pytest.fixture
def copilot_manifest(tmp_path):
    copilot_dir = tmp_path / "copilot" / "my-service"
    copilot_dir.mkdir(parents=True)
    manifest_path = copilot_dir / "manifest.yml"
    manifest_content = {
        "name": "my-service",
        "type": "Load Balanced Web Service",
        "environments": {"dev": {"http": {"alb": "alb-arn", "alias": "test.alias.com"}}},
        "variables": {"S3_BUCKET_NAME": "${COPILOT_APPLICATION_NAME}-${COPILOT_ENVIRONMENT_NAME}"},
    }
    with open(manifest_path, "w") as f:
        yaml.safe_dump(manifest_content, f)
    return tmp_path


def test_migrate_copilot_manifests_creates_services_directory_and_files(tmp_path, copilot_manifest):
    output_dir = tmp_path / "services"
    file_path = output_dir / "my-service/service-config.yml"

    os.chdir(tmp_path)
    service_manager = ServiceManager()
    service_manager.migrate_copilot_manifests()

    assert file_path.exists()


def test_migrate_copilot_manifests_generates_expected_service_config(tmp_path, copilot_manifest):
    expected_service_config = {
        "name": "my-service",
        "type": "Load Balanced Web Service",
        "environments": {"dev": {"http": {"alias": "test.alias.com"}}},
        "variables": {
            "S3_BUCKET_NAME": "${PLATFORM_APPLICATION_NAME}-${PLATFORM_ENVIRONMENT_NAME}"
        },
    }

    os.chdir(tmp_path)
    service_manager = ServiceManager()
    service_manager.migrate_copilot_manifests()

    with open(tmp_path / "services/my-service/service-config.yml") as f:
        service_config = yaml.safe_load(f)

    assert service_config == expected_service_config


def test_migrate_copilot_manifests_skips_unwanted_service_types(tmp_path):
    copilot_dir = tmp_path / "copilot" / "my-service"
    copilot_dir.mkdir(parents=True)
    manifest_path = copilot_dir / "manifest.yml"
    manifest_content = {"name": "my-service", "type": "Scheduled Job"}
    with open(manifest_path, "w") as f:
        yaml.safe_dump(manifest_content, f)

    output_dir = tmp_path / "services"
    file_path = output_dir / "my-service/service-config.yml"

    os.chdir(tmp_path)
    service_manager = ServiceManager()
    service_manager.migrate_copilot_manifests()

    assert not file_path.exists()
