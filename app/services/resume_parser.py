import os
from pypdf import PdfReader
from docx import Document


def extract_pdf_text(file_path):
    """Extract text from a PDF file."""
    try:
        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        text = '\n'.join(text_parts)
        return clean_text(text)
    except Exception as e:
        print(f'PDF extraction error: {e}')
        return ''


def extract_docx_text(file_path):
    """Extract text from a DOCX file."""
    try:
        doc = Document(file_path)
        text_parts = []

        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text.strip())

        for table in doc.tables:
            for row in table.rows:
                row_text = ' | '.join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    text_parts.append(row_text)

        text = '\n'.join(text_parts)
        return clean_text(text)
    except Exception as e:
        print(f'DOCX extraction error: {e}')
        return ''


def extract_text(file_path):
    """Extract text from a file based on its extension."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        return extract_pdf_text(file_path)
    elif ext == '.docx':
        return extract_docx_text(file_path)
    else:
        return ''


def clean_text(text):
    """Clean extracted text by normalizing whitespace."""
    import re
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    text = text.strip()
    return text
