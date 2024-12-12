from dbt_platform_helper.domain.maintenance_page import MaintenancePageProvider


class Environment:
    def __init__(self):
        pass

    def offline(self, app, env, svc, template, vpc):
        maintenance_page = MaintenancePageProvider()
        maintenance_page.activate(app, env, svc, template, vpc)

    def online(self, app, env):
        maintenance_page = MaintenancePageProvider()
        maintenance_page.deactivate(app, env)
