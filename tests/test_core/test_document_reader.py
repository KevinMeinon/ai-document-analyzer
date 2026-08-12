from pathlib import Path

from docx import Document

from document_analyzer.core.document_reader import read_document


def test_read_text_and_markdown_documents(tmp_path: Path) -> None:
    text_path = tmp_path / "notes.txt"
    text_path.write_text("plain text", encoding="utf-8")
    markdown_path = tmp_path / "notes.md"
    markdown_path.write_text("# heading\n\nbody", encoding="utf-8")

    assert read_document(text_path).pages[0].text == "plain text"
    assert "# heading" in read_document(markdown_path).content


def test_read_docx_paragraphs_and_tables(tmp_path: Path) -> None:
    path = tmp_path / "notes.docx"
    source = Document()
    source.add_paragraph("A paragraph")
    table = source.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "left"
    table.rows[0].cells[1].text = "right"
    source.save(path)

    document = read_document(path)

    assert "A paragraph" in document.content
    assert "left | right" in document.content
