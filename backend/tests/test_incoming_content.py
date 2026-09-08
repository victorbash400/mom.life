from app.incoming_content import extract_upload_text


def test_extract_upload_text_preserves_text_and_reports_unsupported_files():
    assert extract_upload_text(b"Permission due Friday", "text/plain", "notice.txt") == "Permission due Friday"
    unsupported = extract_upload_text(b"image", "image/jpeg", "notice.jpg")
    assert "No text extractor is available" in unsupported


def test_extract_upload_text_reports_invalid_pdf_without_breaking_upload():
    extracted = extract_upload_text(b"not a pdf", "application/pdf", "notice.pdf")
    assert extracted.endswith("Text extraction failed.")
