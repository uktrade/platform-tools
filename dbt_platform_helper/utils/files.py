import click
import yaml
from jinja2 import Environment
from jinja2 import FileSystemLoader

from dbt_platform_helper.providers.files import FileProvider


def to_yaml(value):
    return yaml.dump(value, sort_keys=False)


# TODO - extract file provider functionality from this - and figure out what it actually does!
# Move to the new file provider - or potentially copilot?
def generate_override_files(base_path, file_path, output_dir):
    def generate_files_for_dir(pattern):
        for file in file_path.glob(pattern):
            if file.is_file():
                contents = file.read_text()
                file_name = str(file).removeprefix(f"{file_path}/")
                click.echo(
                    FileProvider.mkfile(
                        base_path,
                        output_dir / file_name,
                        contents,
                        overwrite=True,
                    )
                )

    generate_files_for_dir("*")
    generate_files_for_dir("bin/*")


def generate_override_files_from_template(base_path, overrides_path, output_dir, template_data={}):
    templates = Environment(
        loader=FileSystemLoader(f"{overrides_path}"), keep_trailing_newline=True
    )
    environments = ",".join([env["name"] for env in template_data["environments"]])
    data = {"environments": environments}

    def generate_files_for_dir(pattern):

        for file in overrides_path.glob(pattern):
            if file.is_file():
                file_name = str(file).removeprefix(f"{overrides_path}/")
                contents = templates.get_template(str(file_name)).render(data)
                message = FileProvider.mkfile(
                    base_path, output_dir / file_name, contents, overwrite=True
                )
                click.echo(message)

    generate_files_for_dir("*")
    generate_files_for_dir("bin/*")
