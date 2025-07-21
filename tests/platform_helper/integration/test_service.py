import json
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import create_autospec
from unittest.mock import patch

import pytest
from freezegun import freeze_time

from dbt_platform_helper.domain.service import ServiceManger
from dbt_platform_helper.entities.semantic_version import SemanticVersion
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.version import InstalledVersionProvider
from tests.platform_helper.conftest import EXPECTED_FILES_DIR


@pytest.mark.parametrize(
    "input_args, expected_terraform_file",
    [
        (
            {"environments": ["development"], "services": [], "flag_image_tag": None},
            "default_image_tag.json",
        ),
        (
            {"environments": ["development"], "services": [], "flag_image_tag": "doesnt-matter"},
            "flag_image_tag.json",
        ),
    ],
)
@patch("dbt_platform_helper.domain.service.version", return_value="14.0.0")
@patch("dbt_platform_helper.providers.terraform_manifest.version", return_value="14.0.0")
@freeze_time("2025-01-16 13:00:00")
def test_generate(
    mock_version,
    fakefs,
    create_valid_platform_config_file,
    create_valid_service_config_file,
    mock_application,
    input_args,
    expected_terraform_file,
):

    # Test setup
    load_application = Mock()
    load_application.return_value = mock_application
    mock_installed_version_provider = create_autospec(spec=InstalledVersionProvider, spec_set=True)
    mock_installed_version_provider.get_semantic_version.return_value = SemanticVersion(14, 0, 0)
    mock_config_validator = Mock(spec=ConfigValidator)
    mock_config_provider = ConfigProvider(
        mock_config_validator, installed_version_provider=mock_installed_version_provider
    )

    io = MagicMock()
    service_manager = ServiceManger(
        config_provider=mock_config_provider,
        io=io,
        load_application=load_application,
    )

    # Test execution
    service_manager.generate(**input_args)

    # Test Assertion
    actual_terraform = Path(f"terraform/services/development/web/main.tf.json")
    expected_terraform = EXPECTED_FILES_DIR / Path(f"terraform/services/{expected_terraform_file}")
    actual_yaml = Path(f"terraform/services/development/web/service-config.yml")

    assert actual_terraform.exists()
    assert actual_yaml.exists()

    content = actual_terraform.read_text()
    expected_content = expected_terraform.read_text()
    actual_json_content = json.loads(content)
    expected_json_content = json.loads(expected_content)

    assert actual_json_content == expected_json_content

    # TODO check
    # not environment overrides in service-config
    # check environment overrides applied
