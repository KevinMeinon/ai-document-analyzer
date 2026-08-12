"""Pydantic AI analysis over locally extracted PDF text and Chroma context."""

from typing import Any, cast

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent, RunContext

from document_analyzer.core.pdf_reader import PdfDocument
from document_analyzer.core.settings import Settings
from document_analyzer.services.chroma_service import ChromaDocumentStore, RetrievedChunk


class AnalysisContext(BaseModel):
    """Pydantic dependency object supplied to every agent run."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    document: PdfDocument
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    store: Any = Field(default=None, exclude=True)


class PdfAnalysisResult(BaseModel):
    """Structured response returned by the analysis agent."""

    answer: str = Field(description="Summary or answer grounded in the supplied context")
    context: str = Field(description="Evidence used to produce the answer")
    sources: list[str] = Field(default_factory=list, description="Source filenames and page numbers")


def build_agent(settings: Settings) -> Agent[AnalysisContext, PdfAnalysisResult]:
    """Build an agent with the configured model and typed dependencies."""

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for document analysis")

    agent = Agent(
        settings.llm_model,
        deps_type=AnalysisContext,
        output_type=PdfAnalysisResult,
        system_prompt=(
            "You analyze PDF documents. Use only the extracted document context supplied here "
            "and retrieved prior-document context. Never claim to have opened or uploaded a PDF. "
            "If the evidence is insufficient, say so clearly. Keep answers concise."
        ),
    )

    @agent.system_prompt
    def add_pdf_context(ctx: RunContext[AnalysisContext]) -> str:
        document = ctx.deps.document
        current = document.content[: settings.chunk_size * settings.retrieval_limit]
        prior = "\n".join(
            f"[{chunk.filename}, page {chunk.page_number}] {chunk.text}" for chunk in ctx.deps.retrieved_chunks
        )
        return (
            f"Current document: {document.filename}\n"
            f"Current document text:\n{current}\n\n"
            f"Relevant indexed-document context (use only when relevant):\n{prior or '[none]'}"
        )

    @agent.tool
    def search_prior_documents(ctx: RunContext[AnalysisContext], query: str) -> list[RetrievedChunk]:
        """Search all previously indexed PDF chunks for additional context."""

        if ctx.deps.store is None:
            return []
        return ctx.deps.store.search(query)

    return cast("Agent[AnalysisContext, PdfAnalysisResult]", agent)


async def analyze_document(
    document: PdfDocument,
    prompt: str,
    store: ChromaDocumentStore,
    settings: Settings,
) -> PdfAnalysisResult:
    """Run summary or question analysis against a retained PDF."""

    logger.debug(
        "Started LLM analysis for {} with a {} character prompt using {}",
        document.document_id,
        len(prompt),
        settings.llm_model,
    )
    context = AnalysisContext(
        document=document,
        retrieved_chunks=store.search(prompt),
        store=store,
    )
    result = await build_agent(settings).run(prompt, deps=context)
    logger.info(
        "Completed LLM analysis for {} after retrieving {} chunks and {} sources",
        document.document_id,
        len(context.retrieved_chunks),
        len(result.output.sources),
    )
    return result.output
