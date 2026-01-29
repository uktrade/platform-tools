from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import create_autospec

import pytest

from dbt_platform_helper.domain.codebase import Codebase
from dbt_platform_helper.entities.semantic_version import SemanticVersion
from dbt_platform_helper.providers.aws.codepipeline import CodePipeline
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.config_validator import ConfigValidator
from dbt_platform_helper.providers.ecs import ECS
from dbt_platform_helper.providers.files import LocalFileSystem
from dbt_platform_helper.providers.version import InstalledVersionProvider


def mock_start_pipeline_execution(**kwargs):
    # TODO add a call tracking count and gives different responses
    if kwargs == {
        "name": "test-application-application-manual-release",
        "variables": [
            {"name": "IMAGE_TAG", "value": "commit-id"},
            {"name": "ENVIRONMENT", "value": "development"},
        ],
    }:
        return {"pipelineExecutionId": "doesnt-matter-id"}
    else:
        raise Exception("end")


def mock_get_pipeline_execution(**kwargs):
    if kwargs == {
        "pipelineName": "test-application-application-manual-release",
        "pipelineExecutionId": "doesnt-matter-id",
    }:
        return {
            "pipelineExecution": {
                "pipelineName": "test-application-application-manual-release",
                "status": "Succeeded",
            }
        }
    else:
        raise Exception("end")


def mock_describe_task_definition(**kwargs):
    task_def = kwargs.get("taskDefinition")
    if task_def == "web-task-def-arn":
        return {
            "taskDefinition": {
                "family": "web-task-def",
                "taskDefinitionArn": "web-task-def-arn",
                "containerDefinitions": [
                    {"name": "ipfilter"},
                    {"name": "appconfig"},
                    {"name": "web", "image": "image-doesnt-matter:commit-id"},
                ],
            }
        }
    elif task_def == "celery-beat-task-def-arn":
        return {
            "taskDefinition": {
                "family": "celery-beat-task-def",
                "taskDefinitionArn": "celery-beat-task-def-arn",
                "containerDefinitions": [
                    {"name": "ipfilter"},
                    {"name": "appconfig"},
                    {"name": "celery-beat", "image": "image-doesnt-matter:commit-id"},
                ],
            }
        }
    elif task_def == "celery-worker-task-def-arn":
        return {
            "taskDefinition": {
                "family": "celery-worker-task-def",
                "taskDefinitionArn": "celery-worker-task-def-arn",
                "containerDefinitions": [
                    {"name": "ipfilter"},
                    {"name": "appconfig"},
                    {"name": "celery-worker", "image": "image-doesnt-matter:commit-id"},
                ],
            }
        }
    else:
        raise Exception(f"Task definition not found: {task_def}")


@pytest.mark.parametrize(
    "input_args",
    [
        {
            "app": "test-application",
            "env": "development",
            "codebases": ["application"],
        },
        {
            "app": "test-application",
            "env": "development",
            "codebases": ["application"],
            "wait": False,
        },
        # ({"app": "test-application", "env": "development", "codebases": []}, "none"),
    ],
)
def test_redeploy(mock_application, fakefs, create_valid_platform_config_file, input_args):

    mock_codepipeline = Mock()
    mock_codepipeline.start_pipeline_execution.side_effect = mock_start_pipeline_execution
    mock_codepipeline.get_pipeline.return_value = True
    mock_codepipeline.get_pipeline_execution.side_effect = mock_get_pipeline_execution
    mock_session = Mock()
    mock_session.client.return_value = mock_codepipeline
    mock_ecs = Mock()
    mock_ecs.describe_services.return_value = {
        "services": [
            {
                "serviceArn": "arn-doesnt-matter/celery-beat",
                "serviceName": "test-application-development-web",
                "clusterArn": "arn-doesnt-matter",
                "taskDefinition": "web-task-def-arn",
            },
            {
                "serviceArn": "arn-doesnt-matter/celery-beat",
                "serviceName": "test-application-development-celery-beat-ran",
                "clusterArn": "arn-doesnt-matter",
                "taskDefinition": "celery-beat-task-def-arn",
            },
            {
                "serviceArn": "arn-doesnt-matter/celery-worker",
                "serviceName": "test-application-development-celery-worker",
                "clusterArn": "arn-doesnt-matter",
                "taskDefinition": "celery-worker-task-def-arn",
            },
        ]
    }
    mock_ecs.get_paginator.return_value.paginate.return_value = [
        {
            "serviceArns": [
                "arn-doesnt-matter/web",
                "arn-doesnt-matter/celery-beat",
                "arn-doesnt-matter/celery-worker",
            ],
        }
    ]
    mock_ecs.describe_task_definition.side_effect = mock_describe_task_definition
    mock_ssm = Mock()

    io = MagicMock()

    mock_installed_version_provider = create_autospec(spec=InstalledVersionProvider, spec_set=True)
    mock_installed_version_provider.get_semantic_version.return_value = SemanticVersion(14, 0, 0)
    mock_config_validator = Mock(spec=ConfigValidator)
    cb = Codebase(
        parameter_provider=Mock(),  # not used in redeploy
        load_application=Mock(),  # not used in redeploy
        io=io,
        config=ConfigProvider(
            mock_config_validator, installed_version_provider=mock_installed_version_provider
        ),
        pipeline=CodePipeline(mock_session),
        deployment=ECS(
            ecs_client=mock_ecs,
            ssm_client=mock_ssm,
            application_name="test-application",
            env=input_args["env"],
        ),
        file_system=LocalFileSystem(),
    )

    result = cb.redeploy(**input_args)

    assert result[0].codebase == "application"
    assert result[0].pipeline == "test-application-application-manual-release"
    assert result[0].execution_id == "doesnt-matter-id"
    assert result[0].tag == "commit-id"
    assert not result[0].error
    if input_args.get("wait", True):
        assert result[0].status == "succeeded"
    else:
        assert result[0].status == "triggered"
        assert (
            result[0].url
            == "https://eu-west-2.console.aws.amazon.com/codesuite/codepipeline/pipelines/test-application-application-manual-release/executions/doesnt-matter-id"
        )


"""
Tests: 
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
"""
