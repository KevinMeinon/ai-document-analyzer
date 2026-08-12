from pathlib import Path

import pytest

from document_analyzer.core.settings import Settings
from document_analyzer.services.document_storage import store_uploaded_file


def test_store_uploaded_file_uses_generated_directory(tmp_path: Path) -> None:
    identifier, path = store_uploaded_file("../report.txt", b"hello", Settings(upload_dir=tmp_path))

    assert path == tmp_path / str(identifier) / "report.txt"
    assert path.read_bytes() == b"hello"


def test_store_uploaded_file_rejects_unsupported_extension(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="supported"):
        store_uploaded_file("report.exe", b"hello", Settings(upload_dir=tmp_path))
