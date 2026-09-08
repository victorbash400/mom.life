from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from pypdf import PdfReader
from pypdf.errors import PyPdfError


MAX_INTAKE_TEXT = 50_000


def extract_upload_text(content: bytes, media_type: str, filename: str) -> str:
    kind = media_type.casefold()
    suffix = Path(filename).suffix.casefold()
    try:
        if kind.startswith("text/") or kind in {"application/json", "application/xml"}:
            text = content.decode("utf-8", errors="replace")
        elif kind == "application/pdf" or suffix == ".pdf":
            text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages)
        elif kind == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or suffix == ".docx":
            with ZipFile(BytesIO(content)) as archive:
                root = ElementTree.fromstring(archive.read("word/document.xml"))
            text = " ".join(part.strip() for part in root.itertext() if part.strip())
        else:
            return f"Uploaded file: {filename}\nMedia type: {media_type}\nNo text extractor is available for this file type."
    except (BadZipFile, ElementTree.ParseError, KeyError, OSError, PyPdfError, ValueError):
        return f"Uploaded file: {filename}\nMedia type: {media_type}\nText extraction failed."
    clean = text.strip()
    if not clean:
        return f"Uploaded file: {filename}\nMedia type: {media_type}\nThe file contains no extractable text."
    return clean[:MAX_INTAKE_TEXT]
