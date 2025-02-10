from os import makedirs
from pathlib import Path


class FileProvider:

    def load(path: str) -> str:
        pass

    @staticmethod
    def mkfile(base_path: str, file_path: str, contents: str, overwrite=False) -> str:
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

    @staticmethod
    def delete_file(base_path: str, file: str):
        file_path = Path(base_path) / file
        if file_path.exists():
            file_path.unlink()
            return f"{str(file_path)} has been deleted"
