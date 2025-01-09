import os
from pathlib import Path

from dbt_platform_helper.utils.files import generate_override_files
from dbt_platform_helper.utils.files import generate_override_files_from_template


def test_generate_override_files(fakefs):
    """Test that, given a path to override files and an output directory,
    generate_override_files copies the required files to the output
    directory."""

    fakefs.create_file("templates/.gitignore")
    fakefs.create_file("templates/bin/code.ts")
    fakefs.create_file("templates/node_modules/package.ts")

    generate_override_files(
        base_path=Path("."), file_path=Path("templates"), output_dir=Path("output")
    )

    assert ".gitignore" in os.listdir("/output")
    assert "code.ts" in os.listdir("/output/bin")
    assert "node_modules" not in os.listdir("/output")


def test_generate_pipeline_override_files(fakefs):
    """Test that generate_pipeline_override_files copies and renders the
    required files along with templated data to the output directory."""

    fakefs.create_file("templates/.gitignore", contents="This is the .gitignore template.")
    fakefs.create_file("templates/bin/code.ts", contents="This is the code.ts template.")
    fakefs.create_file(
        "templates/node_modules/package.ts", contents="This is the package.ts template."
    )
    fakefs.create_file(
        "templates/buildspec.deploy.yml", contents="Contains {{ environments }} environments."
    )

    template_data = {"environments": [{"name": "dev"}, {"name": "prod"}]}

    generate_override_files_from_template(
        base_path=Path("."),
        overrides_path=Path("templates"),
        output_dir=Path("output"),
        template_data=template_data,
    )

    assert os.path.isfile("output/.gitignore")
    assert os.path.isfile("output/bin/code.ts")
    assert not os.path.exists("output/node_modules")

    with open("output/.gitignore", "r") as f:
        assert f.read() == "This is the .gitignore template."

    with open("output/bin/code.ts", "r") as f:
        assert f.read() == "This is the code.ts template."

    with open("output/buildspec.deploy.yml", "r") as f:
        assert f.read() == "Contains dev,prod environments."
