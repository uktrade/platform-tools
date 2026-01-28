from unittest.mock import Mock
from unittest.mock import create_autospec

import pytest

from dbt_platform_helper.domain.codebase import Codebase
from dbt_platform_helper.entities.semantic_version import SemanticVersion
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.version import InstalledVersionProvider


@pytest.mark.parametrize(
    "input_args, params_exist",
    [
        ({"app": "test-application", "env": "development", "codebases": ["application"]}, "none"),
        # ({"app": "test-application", "env": "development", "codebases": []}, "exists"),
        # ({"app": "test-application", "env": "development", "codebases": []}, "none"),
    ],
)
def test_redeploy(fakefs, create_valid_platform_config_file, input_args, params_exist):

    mock_deployment = Mock()
    mock_deployment.get_deployed_services.return_value = [
        # DeployedService(
        #     commit="doesnt-matter",
        #     environment="development",
        #     name="web"
        # ),
        # DeployedService(
        #     commit="doesnt-matter",
        #     environment="development",
        #     name="celery-beat"
        # ),
        # DeployedService(
        #     commit="doesnt-matter",
        #     environment="development",
        #     name="celery-worker"
        # )
    ]
    mock_installed_version_provider = create_autospec(spec=InstalledVersionProvider, spec_set=True)
    mock_installed_version_provider.get_semantic_version.return_value = SemanticVersion(14, 0, 0)
    cb = Codebase(
        parameter_provider=Mock(),
        load_application=Mock(),
        config=ConfigProvider(installed_version_provider=mock_installed_version_provider),
        deployment=mock_deployment,
    )

    result = cb.redeploy(**input_args)

    assert result == {
        "application": {
            "services": {"celery-worker": "", "celery-beat": "", "web": ""},
            # "tag": "commit-doesnt-matter"
        }
    }


# @pytest.mark.parametrize(
#     "input_args, params_exist",
#     [
#         ({"app": "test-application", "env": "development", "codebases": ["application"]}, "none"),
#         # ({"app": "test-application", "env": "development", "codebases": []}, "exists"),
#         # ({"app": "test-application", "env": "development", "codebases": []}, "none"),
#     ],
# )
# def test_redeploy_mistmatch(
#     fakefs,
#     create_valid_platform_config_file,
#     input_args,
#     params_exist
#     ):

#     mock_deployment = Mock()
#     mock_deployment.get_deployed_services.return_value = [
#         DeployedService(
#             commit="doesnt",
#             environment="development",
#             name="web"
#         ),
#         DeployedService(
#             commit="doesnt-matter",
#             environment="development",
#             name="celery-beat"
#         ),
#         DeployedService(
#             commit="doesnt-matter",
#             environment="development",
#             name="celery-worker"
#         )
#     ]
#     mock_installed_version_provider = create_autospec(spec=InstalledVersionProvider, spec_set=True)
#     mock_installed_version_provider.get_semantic_version.return_value = SemanticVersion(14, 0, 0)
#     cb = Codebase(
#             parameter_provider =  Mock(),
#             load_application =  Mock(),
#             config=ConfigProvider(
#                 installed_version_provider=mock_installed_version_provider
#             ),
#             deployment=mock_deployment,
#     )

#     result = cb.redeploy(**input_args)

#     assert result == {"application" : {
#         "services" : {"celery-worker": "", "celery-beat": "", "web": ""},
#         # "tag": "commit-doesnt-matter"
#         }}


"""
Tests:
- integration - happy path
    
- unit
    - no codebases and not in deploy repo
    - no deployed services
    - no codebase_tags
    - deployed tag mismatch
    - no to triggering pipeline
    - trigger deployment exception
    - waiting time exceeded
        - execution status always None
        - execution returned
        - execution is not complete
    - execution 
        - successful
        - failed
- 
"""
