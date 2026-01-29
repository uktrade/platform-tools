from pathlib import Path

from dbt_platform_helper.ports.file_system import FileSystemPort


class FileProvider:

    def load(path: str) -> str:
        pass

    @staticmethod
    def mkfile(base_path: str, file_name: str, contents: str, overwrite=False) -> str:
        file_path = Path(base_path).joinpath(file_name)
        file_exists = file_path.exists()
        if file_exists and not overwrite:
            return f"File {file_path} exists; doing nothing"

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(contents)

        action = "overwritten" if file_exists and overwrite else "created"
        return f"File {file_path} {action}"

    @staticmethod
    def delete_file(base_path: str, file_name: str):
        file_path = Path(base_path) / file_name
        if file_path.exists():
            file_path.unlink()
            return f"{str(file_path)} has been deleted"


class LocalFileSystem(FileSystemPort):

    def get_current_directory(self):
        return Path.cwd()
