import os
import re
import pdfplumber
from docx import Document


def extract_pdf_text(file_path):
    """Extract text from a PDF file using pdfplumber for better layout handling."""
    try:
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text(
                    x_tolerance=2,
                    y_tolerance=2
                )
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


def defragment_text(text):
    """Rejoin fragmented text from PDFs that output word-by-word.

    Handles cases where each word is on its own line separated by blank lines.
    """
    lines = text.split('\n')
    merged = []
    buffer = ''

    for line in lines:
        stripped = line.strip()

        # Empty line = paragraph break
        if not stripped:
            if buffer:
                merged.append(buffer)
                buffer = ''
            merged.append('')
            continue

        # Single word or very short fragment - join with previous
        if len(stripped.split()) == 1 and len(stripped) > 1:
            if buffer and not buffer[-1] in '.!?:;':
                buffer += ' ' + stripped
            else:
                if buffer:
                    merged.append(buffer)
                buffer = stripped
        else:
            # Multi-word line - join with buffer if no sentence ending
            if buffer and not buffer[-1] in '.!?:;':
                buffer += ' ' + stripped
            else:
                if buffer:
                    merged.append(buffer)
                buffer = stripped

    if buffer:
        merged.append(buffer)

    return '\n'.join(merged)


def clean_text(text):
    """Clean extracted text by normalizing whitespace and fixing fragmentation."""
    # Fix word-by-word fragmentation from PDFs
    text = defragment_text(text)
    # Collapse multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Collapse multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    text = text.strip()
    return text
