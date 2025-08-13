import os

import pytest
import yaml

from dbt_platform_helper.providers.schema_migrations.schema_v1_to_v2_migration import (
    SchemaV1ToV2Migration,
)


@pytest.fixture
def platform_config():
    return {"application": "my-app"}


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


class TestSchemaV1oV2Migration:
    def test_from_version(self):
        migration = SchemaV1ToV2Migration()
        assert migration.from_version() == 1

    def test_migration_creates_services_directory_and_files(
        self, tmp_path, copilot_manifest, platform_config
    ):
        output_dir = tmp_path / "services"
        file_path = output_dir / "my-service/service-config.yml"

        os.chdir(tmp_path)
        migration = SchemaV1ToV2Migration()
        migration.migrate(platform_config)

        assert file_path.exists()

    def test_migration_generates_expected_service_config(
        self, tmp_path, copilot_manifest, platform_config
    ):
        expected_service_config = {
            "name": "my-service",
            "type": "Load Balanced Web Service",
            "environments": {"dev": {"http": {"alias": "test.alias.com"}}},
            "variables": {"S3_BUCKET_NAME": "my-app-${PLATFORM_ENVIRONMENT_NAME}"},
        }

        os.chdir(tmp_path)
        migration = SchemaV1ToV2Migration()
        migration.migrate(platform_config)

        with open(tmp_path / "services/my-service/service-config.yml") as f:
            service_config = yaml.safe_load(f)

        assert service_config == expected_service_config

    def test_migration_skips_unwanted_service_types(self, tmp_path, platform_config):
        copilot_dir = tmp_path / "copilot" / "my-service"
        copilot_dir.mkdir(parents=True)
        manifest_path = copilot_dir / "manifest.yml"
        manifest_content = {"name": "my-service", "type": "Scheduled Job"}
        with open(manifest_path, "w") as f:
            yaml.safe_dump(manifest_content, f)

        output_dir = tmp_path / "services"
        file_path = output_dir / "my-service/service-config.yml"

        os.chdir(tmp_path)
        migration = SchemaV1ToV2Migration()
        migration.migrate(platform_config)

        assert not file_path.exists()
