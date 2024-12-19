from os import makedirs
from pathlib import Path

import click
import yaml
from jinja2 import Environment
from jinja2 import FileSystemLoader


def to_yaml(value):
    return yaml.dump(value, sort_keys=False)


def mkfile(base_path, file_path, contents, overwrite=False):
    file_path = Path(file_path)
    file = Path(base_path).joinpath(file_path)
    file_exists = file.exists()

    if not file_path.parent.exists():
        makedirs(file_path.parent)

    if file_exists and not overwrite:
        return f"File {file_path} exists; doing nothing"

    action = "overwritten" if file_exists and overwrite else "created"

    file.write_text(contents)

    return f"File {file_path} {action}"


def generate_override_files(base_path, file_path, output_dir):
    def generate_files_for_dir(pattern):
        for file in file_path.glob(pattern):
            if file.is_file():
                contents = file.read_text()
                file_name = str(file).removeprefix(f"{file_path}/")
                click.echo(
                    mkfile(
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
                message = mkfile(base_path, output_dir / file_name, contents, overwrite=True)
                click.echo(message)

    generate_files_for_dir("*")
    generate_files_for_dir("bin/*")
