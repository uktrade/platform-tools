from unittest.mock import Mock

from dbt_platform_helper.domain.copilot import Copilot


class CopilotMocks:
    def __init__(self, **kwargs):
        self.config_provider = kwargs.get("config_provider", Mock())
        self.parameter_provider = kwargs.get("parameter_provider", Mock())
        self.file_provider = kwargs.get("file_provider", Mock())
        self.copilot_templating = kwargs.get("copilot_templating", Mock())
        self.kms_provider = kwargs.get("kms_provider", Mock())
        self.io = kwargs.get("io", Mock())

    def params(self):
        return {
            "config_provider": self.config_provider,
            "parameter_provider": self.parameter_provider,
            "file_provider": self.file_provider,
            "copilot_templating": self.copilot_templating,
            "kms_provider": self.kms_provider,
            "io": self.io,
        }


class TestCopilot:

    def test_copilot_make_addons_success(self):

        mocks = CopilotMocks()
        copilot_obj = Copilot(**mocks.params())
        copilot_obj.make_addons()
