from pathlib import Path

import yaml

from dbt_platform_helper.domain.plans import PlanLoader
from tests.platform_helper.conftest import FIXTURES_DIR


def test_loads_plans(fakefs):
    manager = PlanLoader()

    result = manager.load()

    expected_result = yaml.safe_load(
        Path(FIXTURES_DIR, "plans", "expected", "expected_plans.yml").read_text()
    )

    assert result == expected_result


def test_get_plan_names():
    manager = PlanLoader(extensions={"doesnt-matter": "doesnt-matter"})
    manager._cache = {
        "doesnt-matter": {
            "plan-1": {},
            "plan-2": {},
            "plan-3": {},
        }
    }

    result = manager.get_plan_names("doesnt-matter")

    assert result == ["plan-1", "plan-2", "plan-3"]
