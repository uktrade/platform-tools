import json
import os
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import call
from unittest.mock import create_autospec
from unittest.mock import patch

import pytest
import regex
from freezegun import freeze_time

from dbt_platform_helper.constants import IMAGE_TAG_ENV_VAR
from dbt_platform_helper.constants import (
    TERRAFORM_ECS_SERVICE_MODULE_SOURCE_OVERRIDE_ENV_VAR,
)
from dbt_platform_helper.constants import TERRAFORM_MODULE_SOURCE_TYPE_ENV_VAR
from dbt_platform_helper.domain.service import ServiceManager
from dbt_platform_helper.entities.semantic_version import SemanticVersion
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.version import InstalledVersionProvider
from tests.platform_helper.conftest import EXPECTED_DATA_DIR


@pytest.mark.parametrize(
    "input_args, env_vars, expected_results, expect_exception",
    [
        (
            {"environments": ["development"], "services": []},
            {
                TERRAFORM_MODULE_SOURCE_TYPE_ENV_VAR: "OVERRIDE",
                TERRAFORM_ECS_SERVICE_MODULE_SOURCE_OVERRIDE_ENV_VAR: "source_no_matter",
            },
            None,  # Image tag not given, hence why not relevant - should throw an exception before generating main.tf.json contents
            True,
        ),
        (
            {"environments": ["development"], "services": [], "image_tag_flag": "doesnt-matter"},
            {TERRAFORM_MODULE_SOURCE_TYPE_ENV_VAR: "LOCAL"},
            {"development": "image_tag_flag.json"},
            False,
        ),
        (
            {"environments": ["development"], "services": []},
            {TERRAFORM_MODULE_SOURCE_TYPE_ENV_VAR: "LOCAL", IMAGE_TAG_ENV_VAR: "doesnt-matter"},
            {"development": "image_tag_flag.json"},
            False,
        ),
        (
            {"environments": [], "services": []},
            {
                TERRAFORM_MODULE_SOURCE_TYPE_ENV_VAR: "OVERRIDE",
                IMAGE_TAG_ENV_VAR: "some-fake-image",
            },
            {
                "development": "development.json",
                "staging": "staging.json",
                "production": "production.json",
            },
            False,
        ),
    ],
)
@patch(
    "dbt_platform_helper.domain.service.version", return_value="14.0.0"
)  # Fakefs breaks the metadata to retrieve package version
@patch("dbt_platform_helper.providers.terraform_manifest.version", return_value="14.0.0")
@freeze_time("2025-01-16 13:00:00")
def test_generate(
    mock_version,
    fakefs,
    create_valid_platform_config_file,
    create_valid_service_config_file,
    mock_application,
    input_args,
    env_vars,
    expected_results,
    expect_exception,
):

    # Test setup
    for var, value in env_vars.items():
        os.environ[var] = value
    load_application = Mock()
    load_application.return_value = mock_application
    mock_installed_version_provider = create_autospec(spec=InstalledVersionProvider, spec_set=True)
    mock_installed_version_provider.get_semantic_version.return_value = SemanticVersion(14, 0, 0)
    mock_config_validator = Mock(spec=ConfigValidator)
    mock_config_provider = ConfigProvider(
        mock_config_validator, installed_version_provider=mock_installed_version_provider
    )

    io = MagicMock()
    service_manager = ServiceManager(
        config_provider=mock_config_provider,
        io=io,
        load_application=load_application,
    )

    # Test execution
    if expect_exception:
        with pytest.raises(
            PlatformException,
            match=regex.escape(
                "An image tag must be provided to deploy a service. This can be set by the $IMAGE_TAG environment variable, or the --image-tag flag."
            ),
        ):
            service_manager.generate(**input_args)
    else:
        service_manager.generate(**input_args)

        # Test Assertion
        for environment, file in expected_results.items():
            actual_terraform = Path(
                f"terraform/services/{environment}/web/main.tf.json"
            )  # Path where terraform manifest is generated
            expected_terraform = (
                EXPECTED_DATA_DIR / "services" / "terraform" / f"{file}"
            )  # Location of expected results

            assert actual_terraform.exists()

            actual_content = actual_terraform.read_text()
            expected_content = expected_terraform.read_text()
            actual_json_content = json.loads(actual_content)
            expected_json_content = json.loads(expected_content)

            assert actual_json_content == expected_json_content

        for var, value in env_vars.items():
            del os.environ[var]

    # actual_yaml = Path(f"terraform/services/development/web/service-config.yml")
    # assert actual_yaml.exists()
    # TODO check
    # not environment overrides in service-config
    # check environment overrides applied


@patch("dbt_platform_helper.domain.service.version", return_value="14.0.0")
@patch("dbt_platform_helper.providers.terraform_manifest.version", return_value="14.0.0")
@freeze_time("2025-01-16 13:00:00")
def test_generate_no_service_dir(
    mock_version,
    fakefs,
    create_valid_platform_config_file,
    mock_application,
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
    service_manager = ServiceManager(
        config_provider=mock_config_provider,
        io=io,
        load_application=load_application,
    )

    # Test execution
    with pytest.raises(
        PlatformException,
        match=regex.escape(
            "An image tag must be provided to deploy a service. This can be set by the $IMAGE_TAG environment variable, or the --image-tag flag."
        ),
    ):
        service_manager.generate(environments=[], services=[])

    io.abort_with_error.assert_called_with(
        "Failed extracting services with exception, [Errno 2] No such file or directory in the fake filesystem: '/services'"
    )


@patch("dbt_platform_helper.domain.service.version", return_value="14.0.0")
@patch("dbt_platform_helper.providers.terraform_manifest.version", return_value="14.0.0")
@freeze_time("2025-01-16 13:00:00")
def test_generate_no_service_config(
    mock_version,
    fakefs,
    create_valid_platform_config_file,
    create_service_directory,
    mock_application,
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
    service_manager = ServiceManager(
        config_provider=mock_config_provider,
        io=io,
        load_application=load_application,
    )

    # Test execution
    with pytest.raises(
        PlatformException,
        match=regex.escape(
            "An image tag must be provided to deploy a service. This can be set by the $IMAGE_TAG environment variable, or the --image-tag flag."
        ),
    ):
        service_manager.generate(environments=[], services=[])

    io.warn.assert_has_calls(
        [
            call(
                "Failed loading service name from fake-service.\nPlease ensure that your '/services' directory follows the correct structure (i.e. /services/<service_name>/service-config.yml) and the 'service-config.yml' contents are correct."
            )
        ]
    )


@patch("dbt_platform_helper.domain.service.version", return_value="14.0.0")
@patch("dbt_platform_helper.providers.terraform_manifest.version", return_value="14.0.0")
@freeze_time("2025-01-16 13:00:00")
def test_generate_no_environment(
    mock_version,
    fakefs,
    create_valid_platform_config_file,
    create_service_directory,
    mock_application,
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
    service_manager = ServiceManager(
        config_provider=mock_config_provider,
        io=io,
        load_application=load_application,
    )
    with pytest.raises(
        PlatformException,
        match="""cannot generate terraform for environment doesnt-exist.  It does not exist in your configuration""",
    ):
        service_manager.generate(environments=["doesnt-exist"], services=[])
