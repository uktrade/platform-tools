import pytest

from dbt_platform_helper.providers.files import FileProvider


@pytest.mark.parametrize(
    "file_exists, overwrite, expected_action",
    [
        (False, False, "created"),
        (False, True, "created"),
        (True, True, "overwritten"),
    ],
)
def test_mkfile_creates_or_overrides_the_file(tmp_path, file_exists, overwrite, expected_action):
    filename = "test_file.txt"
    file_path = tmp_path / filename
    if file_exists:
        file_path.touch()

    contents = "The content"

    message = FileProvider().mkfile(str(tmp_path), filename, contents, overwrite)

    assert file_path.exists()
    assert file_path.read_text() == contents
    assert message == f"File {file_path} {expected_action}"


def test_mkfile_does_nothing_if_file_already_exists_but_override_is_false(tmp_path):
    filename = "test_file.txt"
    file_path = tmp_path / filename
    file_path.touch()

    message = FileProvider().mkfile(
        str(tmp_path), filename, contents="does not matter", overwrite=False
    )

    assert message == f"File {file_path} exists; doing nothing"


def test_mkfile_can_write_to_a_file_in_a_non_existent_directory(tmp_path):
    path = tmp_path / "test_dir/test_subdir"
    filename = "test_file.txt"

    message = FileProvider().mkfile(str(path), filename, contents="does not matter")

    file_path = path / filename
    assert file_path.exists()
    assert message == f"File {file_path} created"


def test_delete_file_deletes_the_file(tmp_path):
    folder = "a_folder"
    filename = "some_file.txt"
    folder_path = tmp_path / folder
    file_path = folder_path / filename
    folder_path.mkdir(parents=True)
    file_path.touch()

    message = FileProvider().delete_file(str(folder_path), filename)

    assert not file_path.exists()
    assert message == f"{file_path} has been deleted"


def test_delete_file_does_nothing_if_file_didnt_exist(tmp_path):
    folder = "a_folder"
    filename = "some_file.txt"
    folder_path = tmp_path / folder
    file_path = folder_path / filename

    message = FileProvider().delete_file(str(folder_path), filename)

    assert not file_path.exists()
    assert message is None
