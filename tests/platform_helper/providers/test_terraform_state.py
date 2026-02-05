from dbt_platform_helper.providers.terraform_state import pull_terraform_state


class TestPull:
    def test_exists(self, tmp_path):
        pull_terraform_state(tmp_path)
