"""Persistent ChromaDB indexing and semantic retrieval for PDF chunks."""

from dataclasses import dataclass
from typing import Any, cast

from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from loguru import logger

from document_analyzer.core.pdf_reader import PdfDocument
from document_analyzer.core.settings import Settings


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    text: str
    document_id: str
    filename: str
    page_number: int
    distance: float | None = None


class ChromaDocumentStore:
    """Own one persistent collection containing page-aware PDF chunks."""

    def __init__(self, settings: Settings, collection: Collection | None = None) -> None:
        self.settings = settings
        if collection is not None:
            self.collection = collection
            logger.debug("Initialized Chroma store with an injected collection")
            return

        import chromadb

        settings.chroma_path.mkdir(parents=True, exist_ok=True)
        client: Any = chromadb.PersistentClient(path=str(settings.chroma_path))
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for Chroma embeddings")
        embedding_function = OpenAIEmbeddingFunction(
            api_key=settings.openai_api_key,
            model_name="text-embedding-3-small",
        )
        self.collection = client.get_or_create_collection(
            name=settings.chroma_collection,
            embedding_function=cast(Any, embedding_function),
        )
        logger.info("Initialized Chroma collection {} at {}", settings.chroma_collection, settings.chroma_path)

    def ingest(self, document: PdfDocument) -> int:
        document_id = str(document.metadata.get("document_id", document.document_id))
        logger.debug("Started indexing {} ({})", document.filename, document_id)
        chunks: list[tuple[str, int, str]] = []
        for page in document.pages:
            text = page.text.strip()
            start = 0
            while start < len(text):
                end = min(len(text), start + self.settings.chunk_size)
                chunks.append((text[start:end], page.number, f"{document_id}:{page.number}:{start}"))
                if end == len(text):
                    break
                start = max(end - self.settings.chunk_overlap, start + 1)

        if not chunks:
            raise ValueError(f"No text chunks to index for {document.filename}")

        self.collection.delete(where={"document_id": document_id})
        self.collection.add(
            ids=[chunk[2] for chunk in chunks],
            documents=[chunk[0] for chunk in chunks],
            metadatas=[
                {
                    "document_id": document_id,
                    "filename": document.filename,
                    "file_type": document.file_type,
                    "extraction_method": document.metadata.get("extraction_method", "text"),
                    "ocr_page_count": int(document.metadata.get("ocr_page_count", "0")),
                    "page_number": chunk[1],
                    "source_path": str(document.path),
                }
                for chunk in chunks
            ],
        )
        logger.info("Indexed {} chunks for {}", len(chunks), document.filename)
        return len(chunks)

    def search(
        self,
        query: str,
        limit: int | None = None,
        exclude_document_id: str | None = None,
    ) -> list[RetrievedChunk]:
        """Search indexed chunks, optionally excluding the active document."""
        logger.debug(
            "Chroma search started: query length {}, limit {}, excluding {}",
            len(query),
            limit or self.settings.retrieval_limit,
            exclude_document_id or "no document",
        )
        where = {"document_id": {"$ne": exclude_document_id}} if exclude_document_id else None
        result = self.collection.query(
            query_texts=[query],
            n_results=limit or self.settings.retrieval_limit,
            include=["documents", "metadatas", "distances"],
            where=where,
        )
        result_data = cast(dict[str, Any], result)
        documents = (result_data.get("documents") or [[]])[0]
        metadatas = (result_data.get("metadatas") or [[]])[0]
        distances = (result_data.get("distances") or [[]])[0]
        chunks = [
            RetrievedChunk(
                text=str(text),
                document_id=str(metadata.get("document_id", "")),
                filename=str(metadata.get("filename", "")),
                page_number=int(metadata.get("page_number", 0)),
                distance=float(distances[index]) if index < len(distances) else None,
            )
            for index, (text, metadata) in enumerate(zip(documents, metadatas, strict=False))
        ]
        logger.debug("Chroma search returned {} chunks", len(chunks))
        return chunks

    def count(self) -> int:
        return int(self.collection.count())
