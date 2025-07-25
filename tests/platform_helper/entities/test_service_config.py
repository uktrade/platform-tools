from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from dbt_platform_helper.entities.service import ServiceConfig
from tests.platform_helper.conftest import INPUT_DATA_DIR


@pytest.mark.parametrize(
    "input_data",
    ["minimal-service-config.yml"],
)
def test_service_config(fakefs, input_data):

    input_data = yaml.safe_load(Path(f"{INPUT_DATA_DIR}/services/config/{input_data}").read_text())

    assert ServiceConfig.model_validate(input_data)


def test_invalid_service_config(fakefs):

    input_data = yaml.safe_load(
        Path(f"{INPUT_DATA_DIR}/services/config/invalid-service-config.yml").read_text()
    )

    with pytest.raises(
        ValidationError,
        match="""1 validation error for ServiceConfig\ntype\n  Field required \[type=missing, input_value=\{'name': 'invalid', 'cpu'...GE_TAG}', 'port': 8080}}, input_type=dict\]\n    For further information visit https://errors.pydantic.dev/2.11/v/missing""",
    ):
        ServiceConfig.model_validate(input_data)
