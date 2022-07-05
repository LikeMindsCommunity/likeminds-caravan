import csv
import json
from pathlib import Path


class FileUtilities:

    @staticmethod
    def is_exists_file(file_path: str) -> bool:
        file: Path = Path(file_path)
        return file.is_file()

    @staticmethod
    def write_file_csv(file_path: str, mode: str, data: list) -> None:
        path: Path = Path(file_path)
        path.parent.mkdir(exist_ok=True, parents=True)

        """
            Note: binary mode does not take encoding, newline args,
            returns error if provided
        """
        with open(file_path, mode) as f:
            writer: csv.writer = csv.writer(f)
            writer.writerow(data)

    @staticmethod
    def get_absolute_file_path(file_path: str) -> str:
        absolute_path: Path = Path(file_path).resolve()
        return str(absolute_path)

    @staticmethod
    def remove_file(file_path: str) -> None:
        file: Path = Path(file_path)
        file.unlink()
