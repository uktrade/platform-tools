from unittest.mock import Mock

from dbt_platform_helper.domain.copilot import Copilot


class TestCopilotMakeAddons:

    def test_make_addons_success():

        Copilot(Mock(), Mock(), Mock())
