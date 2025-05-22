from pathlib import Path

from dbt_platform_helper.providers.yaml_file import YamlFileProvider


class PlanLoader:

    PROJECT_DIR = Path(__file__).resolve().parent.parent.parent

    def __init__(
        self,
        extensions: dict = None,
        terraform_dir: str = "terraform",
        loader: YamlFileProvider = YamlFileProvider,
    ):
        self.path = terraform_dir
        self.loader = loader
        self._cache = {}
        self.extensions = extensions or {
            "redis": "elasticache-redis",
            "opensearch": "opensearch",
            "postgres": "postgres",
        }

    def load(self):
        result = {}
        for key, value in self.extensions.items():
            result[key] = self._load_plan(key, f"{self.PROJECT_DIR}/{self.path}/{value}/plans.yml")
        return result

    def _load_plan(self, name, path):
        if name in self._cache:
            return self._cache[name]
        else:
            plan = self.loader.load(path)
            self._cache[name] = plan
            return plan

    def get_plan_names(self, extension):
        plans = self.load()
        return list(plans[extension].keys())
