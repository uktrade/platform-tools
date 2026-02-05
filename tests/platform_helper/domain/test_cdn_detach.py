from dbt_platform_helper.domain.cdn_detach import CDNDetach


class TestCDNDetach:
    def test_exists(self):
        environment_name = "test"
        cdn_detach = CDNDetach()

        cdn_detach.execute(environment_name)
