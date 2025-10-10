import re
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from dbt_platform_helper.entities.service import Cooldown
from dbt_platform_helper.entities.service import Count
from dbt_platform_helper.entities.service import CpuPercentage
from dbt_platform_helper.entities.service import MemoryPercentage
from dbt_platform_helper.entities.service import RequestsPerMinute
from dbt_platform_helper.entities.service import ServiceConfig
from dbt_platform_helper.platform_exception import PlatformException
from tests.platform_helper.conftest import INPUT_DATA_DIR


@pytest.mark.parametrize(
    "input_data",
    ["minimal-service-config.yml"],
)
def test_service_config(fakefs, input_data):

    input_data = yaml.safe_load(Path(f"{INPUT_DATA_DIR}/services/config/{input_data}").read_text())

    assert ServiceConfig.model_validate(input_data)


def test_invalid_writable_directories_service_config(fakefs):

    input_data = yaml.safe_load(
        Path(f"{INPUT_DATA_DIR}/services/config/minimal-service-config.yml").read_text()
    )

    input_data["storage"] = {"writable_directories": ["relative/directory"]}

    with pytest.raises(
        PlatformException,
        match=re.escape("""All writable directory paths must be absolute (starts with a /)"""),
    ):
        ServiceConfig.model_validate(input_data)


def test_invalid_service_config(fakefs):

    input_data = yaml.safe_load(
        Path(f"{INPUT_DATA_DIR}/services/config/invalid-service-config.yml").read_text()
    )

    with pytest.raises(
        ValidationError,
        match="""1 validation error for ServiceConfig\ntype\n  Field required \[type=missing, input_value=\{'name': 'invalid', 'cpu'...GE_TAG}', 'port': 8080}}, input_type=dict\]\n    For further information visit https://errors.pydantic.dev/2.11/v/missing""",
    ):
        ServiceConfig.model_validate(input_data)


def test_web_service_requires_http_block():
    service_config = {
        "name": "web",
        "type": "Load Balanced Web Service",
        "image": {"location": "hub.docker.com/repo:tag", "port": 8080},
        "cpu": 256,
        "memory": 512,
        "count": 1,
    }

    with pytest.raises(
        PlatformException,
        match="A 'http' block must be provided when service type == 'Load Balanced Web Service'",
    ):
        ServiceConfig.model_validate(service_config)


@pytest.mark.parametrize(
    "in_value,out_value,expected_in,expected_out",
    [
        ("30s", "45s", 30, 45),
        (5, 10, 5, 10),
    ],
)
def test_cooldown_parses_seconds_and_ints(in_value, out_value, expected_in, expected_out):
    cd = Cooldown.model_validate({"in": in_value, "out": out_value})
    assert cd.in_ == expected_in
    assert cd.out == expected_out


@pytest.mark.parametrize("bad_in,bad_out", [("two", "VI"), ("10s", "bad"), (None, "5s")])
def test_cooldown_rejects_invalid_values(bad_in, bad_out):
    with pytest.raises(
        PlatformException, match="Cooldown values must be integers or strings like '30s'"
    ):
        Cooldown.model_validate({"in": bad_in, "out": bad_out})


def test_count_requires_at_least_one_dimension():
    with pytest.raises(
        PlatformException, match="If autoscaling is enabled, you must define at least one metric"
    ):
        Count.model_validate({"range": "1-3"})


def test_count_rejects_bad_range_format():
    with pytest.raises(PlatformException, match="Range must be in the format 'int-int' e.g. '1-2'"):
        Count.model_validate({"range": "1 to 3", "cpu_percentage": 50})


@pytest.mark.parametrize("range_value", ["2-1", "5-5"])
def test_count_rejects_min_less_than_max(range_value):
    with pytest.raises(
        PlatformException, match="Range minimum value must be less than the maximum value."
    ):
        Count.model_validate({"range": range_value, "cpu_percentage": 50})


def test_service_config_accepts_int_count():
    service_config = {
        "name": "web",
        "type": "Backend Service",
        "image": {"location": "hub.docker.com/repo:tag", "port": 8080},
        "cpu": 256,
        "memory": 512,
        "count": 1,
    }
    assert ServiceConfig.model_validate(service_config)


def test_count_autoscaling_minimal():
    count = Count.model_validate(
        {"range": "1-3", "cpu_percentage": 70}
    )  # Could've been memory_percentage or requests_per_minute too
    assert count.cpu_percentage == 70
    assert count.range == "1-3"


def test_count_autoscaling_all_the_things():
    count = Count.model_validate(
        {
            "range": "2-5",
            "cooldown": {"in": "5s", "out": "10s"},
            "cpu_percentage": {
                "value": 60,
                "cooldown": {"in": "15s", "out": "25s"},
            },
            "memory_percentage": {
                "value": 80,
                "cooldown": {"in": "35s", "out": "45s"},
            },
            "requests_per_minute": {
                "value": 100,
                "cooldown": {"in": "55s", "out": "65s"},
            },
        }
    )
    assert isinstance(count.cpu_percentage, CpuPercentage)
    assert isinstance(count.memory_percentage, MemoryPercentage)
    assert isinstance(count.requests_per_minute, RequestsPerMinute)

    assert count.cpu_percentage.value == 60
    assert count.cpu_percentage.cooldown.in_ == 15
    assert count.cpu_percentage.cooldown.out == 25

    assert count.memory_percentage.value == 80
    assert count.memory_percentage.cooldown.in_ == 35
    assert count.memory_percentage.cooldown.out == 45

    assert count.requests_per_minute.value == 100
    assert count.requests_per_minute.cooldown.in_ == 55
    assert count.requests_per_minute.cooldown.out == 65
