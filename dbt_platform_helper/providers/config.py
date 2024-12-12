from yamllint import config
from yamllint import linter


class ConfigProvider:
    @staticmethod
    def lint_yaml_for_duplicate_keys(file_path):
        lint_yaml_config = """
        rules:
          key-duplicates: enable
        """
        yaml_config = config.YamlLintConfig(lint_yaml_config)

        with open(file_path, "r") as yaml_file:
            file_contents = yaml_file.read()

            results = linter.run(file_contents, yaml_config)

        parsed_results = [
            "\t"
            + f"Line {result.line}: {result.message}".replace(" in mapping (key-duplicates)", "")
            for result in results
        ]

        return parsed_results
