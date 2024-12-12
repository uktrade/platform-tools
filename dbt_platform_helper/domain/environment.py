from dbt_platform_helper.domain.maintenance_page import MaintenancePageProvider


class Environment:
    def __init__(self, env_name):
        self.env_name = env_name

    def offline(self, app, svc, template, vpc):
        maintenance_page = MaintenancePageProvider()
        maintenance_page.activate(app, self.env_name, svc, template, vpc)

    def online(self, app):
        maintenance_page = MaintenancePageProvider()
        maintenance_page.deactivate(app, self.env_name)
