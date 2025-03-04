from unittest.mock import Mock

from dbt_platform_helper.domain.copilot import Copilot


class CopilotMocks:
    def __init__(self, **kwargs):
        self.parameter_provider = kwargs.get("parameter_provider", Mock())
        self.file_provider = kwargs.get("file_provider", Mock())
        self.config_provider = kwargs.get("config_provider", Mock())
        self.copilot_templating = kwargs.get("copilot_templating", Mock())
        self.io = kwargs.get("io", Mock())

    def params(self):
        return {
            "parameter_provider": self.parameter_provider,
            "file_provider": self.file_provider,
            "config_provider": self.config_provider,
            "copilot_templating": self.copilot_templating,
            "io": self.io,
        }


class TestCopilotMakeAddons:

    def test_make_addons_success(self):

        mocks = CopilotMocks()
        copilot = Copilot(**mocks.params())

        copilot.make_addons()
