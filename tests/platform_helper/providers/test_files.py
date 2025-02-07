import pytest

from dbt_platform_helper.providers.files import FileProvider


@pytest.mark.parametrize(
    "file_exists, overwrite, expected",
    [
        (False, False, "File test_file.txt created"),
        (False, True, "File test_file.txt created"),
        (True, True, "File test_file.txt overwritten"),
    ],
)
def test_mkfile_creates_or_overrides_the_file(tmp_path, file_exists, overwrite, expected):
    filename = "test_file.txt"
    file_path = tmp_path / filename
    if file_exists:
        file_path.touch()

    contents = "The content"

    message = FileProvider().mkfile(str(tmp_path), filename, contents, overwrite)

    assert file_path.exists()
    assert file_path.read_text() == contents
    assert message == expected


def test_mkfile_does_nothing_if_file_already_exists_but_override_is_false(tmp_path):
    filename = "test_file.txt"
    file_path = tmp_path / filename
    file_path.touch()

    message = FileProvider().mkfile(
        str(tmp_path), filename, contents="does not matter", overwrite=False
    )

    assert message == f"File {filename} exists; doing nothing"


@pytest.mark.parametrize("file_exists", [True, False])
def test_delete_file_deletes_the_file(tmp_path, file_exists):
    filename = "some-file.txt"
    file_path = tmp_path / filename
    if file_exists:
        file_path.touch()

    FileProvider().delete_file_if_present(str(tmp_path), filename)

    assert not file_path.exists()
