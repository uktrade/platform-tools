import unittest
from unittest.mock import MagicMock

import pytest
from update_pipeline import update_pipeline_stage_failure


class TestUpdatePipeline(unittest.TestCase):

    def test_update_pipeline_stage_failure_sets_rollback(self):
        mock_client = MagicMock()
        mock_client.get_pipeline.return_value = {
            "pipeline": {
                "name": "test-pipeline",
                "stages": [
                    {
                        "name": "Deploy",
                    }
                ],
            }
        }

        update_pipeline_stage_failure(mock_client, ["test-pipeline"])

        call_args = mock_client.update_pipeline.call_args[1]
        assert call_args["pipeline"]["stages"][0]["onFailure"]["result"] == "ROLLBACK"

    def test_update_pipeline_stage_failure_does_not_set_rollback(self):
        mock_client = MagicMock()
        mock_client.get_pipeline.return_value = {
            "pipeline": {
                "name": "test-pipeline",
                "stages": [
                    {
                        "name": "Source",
                    }
                ],
            }
        }

        with pytest.raises(ValueError) as error_msg:
            update_pipeline_stage_failure(mock_client, ["test-pipeline"])

        assert "Stage Deploy not found in pipeline test-pipeline" in str(error_msg.value)

    def test_update_pipeline_stage_failure_sets_rollback_multiple_stages(self):
        mock_client = MagicMock()
        mock_client.get_pipeline.return_value = {
            "pipeline": {
                "name": "test-pipeline",
                "stages": [
                    {
                        "name": "Source",
                    },
                    {
                        "name": "Deploy-Dev",
                    },
                    {
                        "name": "Deploy-Prod",
                    },
                ],
            }
        }

        update_pipeline_stage_failure(mock_client, ["test-pipeline-main, test-pipeline-tagged"])

        call_args = mock_client.update_pipeline.call_args[1]
        assert not hasattr(call_args["pipeline"]["stages"][0], "onFailure")
        assert call_args["pipeline"]["stages"][1]["onFailure"]["result"] == "ROLLBACK"
        assert call_args["pipeline"]["stages"][2]["onFailure"]["result"] == "ROLLBACK"

    def test_update_pipeline_failure_if_pipeline_not_found(self):
        mock_client = MagicMock()

        not_found_exception = mock_client.exceptions.PipelineNotFoundException(
            error_response={
                "Error": {"Code": "PipelineNotFoundException", "Message": "Pipeline not found"}
            },
            operation_name="GetPipeline",
        )
        mock_client.get_pipeline.side_effect = Exception(not_found_exception)

        with pytest.raises(Exception) as error_msg:
            update_pipeline_stage_failure(mock_client, ["non-existing-pipeline"])

        assert "PipelineNotFoundException" in str(error_msg.value)
