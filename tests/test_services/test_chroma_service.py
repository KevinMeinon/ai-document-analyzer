from pathlib import Path

from document_analyzer.core.pdf_reader import PdfDocument, PdfPage
from document_analyzer.core.settings import Settings
from document_analyzer.services.chroma_service import ChromaDocumentStore


class FakeCollection:
    def __init__(self) -> None:
        self.rows: dict[str, tuple[str, dict]] = {}

    def delete(self, *, where: dict) -> None:
        self.rows = {key: value for key, value in self.rows.items() if value[1]["document_id"] != where["document_id"]}

    def add(self, *, ids: list[str], documents: list[str], metadatas: list[dict]) -> None:
        self.rows.update({key: (text, metadata) for key, text, metadata in zip(ids, documents, metadatas, strict=True)})

    def query(self, **kwargs: object) -> dict:
        rows = list(self.rows.values())
        where = kwargs.get("where")
        if where:
            excluded = str(where["document_id"]["$ne"])  # type: ignore[index]
            rows = [row for row in rows if row[1]["document_id"] != excluded]
        rows = rows[: int(kwargs["n_results"])]
        return {
            "documents": [[row[0] for row in rows]],
            "metadatas": [[row[1] for row in rows]],
            "distances": [[0.1 for _ in rows]],
        }

    def count(self) -> int:
        return len(self.rows)


def test_ingest_is_idempotent_and_search_preserves_page_metadata(tmp_path: Path) -> None:
    settings = Settings(chunk_size=5, chunk_overlap=1)
    collection = FakeCollection()
    store = ChromaDocumentStore(settings, collection=collection)  # type: ignore[arg-type]
    document = PdfDocument(
        path=tmp_path / "sample.pdf",
        filename="sample.pdf",
        metadata={},
        pages=(PdfPage(1, "abcdefghij"),),
    )

    assert store.ingest(document) == 3
    assert store.ingest(document) == 3
    results = store.search("question")

    assert store.count() == 3
    assert results[0].filename == "sample.pdf"
    assert results[0].page_number == 1


def test_search_can_exclude_the_active_document(tmp_path: Path) -> None:
    settings = Settings(chunk_size=20, chunk_overlap=1)
    collection = FakeCollection()
    store = ChromaDocumentStore(settings, collection=collection)  # type: ignore[arg-type]
    current = PdfDocument(
        path=tmp_path / "current.pdf",
        filename="current.pdf",
        metadata={"document_id": "current-id"},
        pages=(PdfPage(1, "current document text"),),
    )
    prior = PdfDocument(
        path=tmp_path / "prior.pdf",
        filename="prior.pdf",
        metadata={"document_id": "prior-id"},
        pages=(PdfPage(1, "prior similar document"),),
    )
    store.ingest(current)
    store.ingest(prior)

    results = store.search("similar", exclude_document_id=current.document_id)

    assert results
    assert all(result.document_id == "prior-id" for result in results)
