from unittest.mock import Mock

from dbt_platform_helper.domain.pipelines import Pipelines


def test_pipeline_generate_with_empty_platform_config_yml_outputs_warning():
    mock_echo = Mock()
    mock_config_provider = Mock()
    mock_config_provider.load_and_validate_platform_config.return_value = {"application": "my-app"}
    pipelines = Pipelines(config_provider=mock_config_provider, echo=mock_echo)

    pipelines.generate(None, None)

    mock_echo.assert_called_once_with("No pipelines defined: nothing to do.", err=True, fg="yellow")


def test_pipeline_generate_with_non_empty_platform_config_but_no_pipelines_outputs_warning():
    mock_echo = Mock()
    mock_config_provider = Mock()
    mock_config_provider.load_and_validate_platform_config.return_value = {"environments": {}}
    pipelines = Pipelines(config_provider=mock_config_provider, echo=mock_echo)

    pipelines.generate(None, None)

    mock_echo.assert_called_once_with("No pipelines defined: nothing to do.", err=True, fg="yellow")
